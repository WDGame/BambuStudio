#include "PrintFinsPoC.hpp"
#include "Plater.hpp"
#include "Selection.hpp"
#include "GUI_App.hpp"
#include "GUI_ObjectList.hpp"
#include "Widgets/WebView.hpp"
#include "libslic3r/Model.hpp"
#include "libslic3r/PrintConfig.hpp"
#include "libslic3r/Utils.hpp"
#include "libslic3r/TriangleMeshSlicer.hpp"
#include <nlohmann/json.hpp>
#include <boost/log/trivial.hpp>
#include <algorithm>
#include <cmath>
#include <wx/dialog.h>
#include <wx/msgdlg.h>
#include <wx/sizer.h>
#include <wx/stattext.h>
#include <wx/timer.h>
#if defined(_WIN32) && wxUSE_WEBVIEW_EDGE
#include <WebView2.h>
#include <wrl/client.h>
#endif

namespace Slic3r::GUI {
namespace {
using Json = nlohmann::json;

int selected_object(Plater &plater)
{
    const auto &selection = plater.get_selection();
    const int index = selection.get_object_idx();
    if ((!selection.is_single_full_instance() && !selection.is_single_full_object()) ||
        index < 0 || size_t(index) >= plater.model().objects.size())
        throw std::runtime_error("Select one complete model on the plate before using PrintFins.");
    return index;
}

Json layer_heights(Plater &plater, const ModelObject &object)
{
    auto config = *plater.config();
    config.apply(object.config.get());
    const double height = config.option<ConfigOptionFloat>("layer_height")->value;
    const double first = config.option<ConfigOptionFloat>("initial_layer_print_height")->value;
    if (!std::isfinite(height) || height <= 0 || !std::isfinite(first) || first <= 0)
        throw std::runtime_error("PrintFins requires positive, constant layer heights.");
    return {{"layerHeight", height}, {"firstLayerHeight", first}};
}

Json posed_mesh(const ModelObject &object)
{
    if (object.instances.size() != 1 || object.volumes.empty())
        throw std::runtime_error("PrintFins supports one instance of a model with plain model parts.");
    if (!object.layer_height_profile.empty() || !object.layer_config_ranges.empty())
        throw std::runtime_error("Variable layer heights and height range modifiers are not supported by PrintFins.");
    Json positions = Json::array();
    for (const ModelVolume *volume : object.volumes) {
        if (volume->name.rfind("PrintFins ", 0) == 0)
            throw std::runtime_error("This model already contains PrintFins. Undo or remove those parts explicitly before generating again.");
        if (!volume->is_model_part())
            throw std::runtime_error("PrintFins does not support modifiers or negative/support volumes.");
        const Transform3d matrix = object.instances.front()->get_matrix() * volume->get_matrix();
        if (!matrix.matrix().allFinite() || std::abs(matrix.linear().determinant()) < 1e-12)
            throw std::runtime_error("The model has an invalid or singular transform.");
        const auto &its = volume->mesh().its;
        if (its.indices.size() > (900000 - positions.size()) / 9)
            throw std::runtime_error("PrintFins currently supports at most 100000 input triangles.");
        for (const auto &face : its.indices) {
            for (int k = 0; k < 3; ++k) {
                const int corner = matrix.linear().determinant() < 0 && k > 0 ? 3 - k : k;
                const Vec3d p = matrix * its.vertices[face[corner]].cast<double>();
                if (!p.allFinite()) throw std::runtime_error("The model contains non-finite vertices.");
                for (int axis = 0; axis < 3; ++axis) positions.push_back(p[axis]);
            }
        }
    }
    if (positions.empty()) throw std::runtime_error("The selected model has no triangles.");
    return positions;
}

class PrintFinsDialog final : public wxDialog {
    Plater &m_plater;
    int m_object_index;
    Json m_request;
    ObjectID m_object_id;
    wxWebView *m_web = nullptr;
    wxStaticText *m_status;
    wxTimer m_timeout;
    bool m_mapped = false;
    bool m_ready = false;
    bool m_busy = false;
    bool m_finished = false;

    void cancel()
    {
        m_finished = true;
        m_timeout.Stop();
        // Destroy the WebView (and its worker) before returning to the project.
        if (m_web) { m_web->Destroy(); m_web = nullptr; }
        EndModal(wxID_CANCEL);
    }

    void fail(const std::string &message)
    {
        if (m_finished) return;
        m_finished = true;
        m_timeout.Stop();
        if (m_web) { m_web->Destroy(); m_web = nullptr; }
        m_status->SetLabel(wxString::FromUTF8(message));
        m_status->Wrap(650);
        Layout();
        BOOST_LOG_TRIVIAL(error) << "PrintFins: " << message;
    }

    void accept(const Json &result)
    {
        if (!result.value("ok", false)) throw std::runtime_error(result.value("error", "PrintFins engine failed."));
        if (!m_plater.can_do_ui_job() || !m_plater.can_add_model())
            throw std::runtime_error("Another operation started; PrintFins result discarded.");
        auto &model = m_plater.model();
        if (selected_object(m_plater) != m_object_index ||
            size_t(m_object_index) >= model.objects.size() || model.objects[m_object_index]->id() != m_object_id)
            throw std::runtime_error("Model selection changed; PrintFins result discarded.");
        ModelObject &object = *model.objects[m_object_index];
        if (posed_mesh(object) != m_request["positions"] || layer_heights(m_plater, object) != m_request["options"])
            throw std::runtime_error("Model or layer settings changed; PrintFins result discarded.");
        const auto triangles = result.at("triangles").get<std::vector<double>>();
        if (triangles.size() % 9 || triangles.size() > 9000000)
            throw std::runtime_error("PrintFins returned invalid or oversized geometry.");
        if (triangles.empty()) {
            m_finished = true;
            m_timeout.Stop();
            wxMessageBox("PrintFins generated no geometry for this model and these settings. The project is unchanged.",
                         "PrintFins", wxOK | wxICON_INFORMATION, this);
            EndModal(wxID_CANCEL);
            return;
        }
        const auto &offset = result.at("offset");
        const Vec3d off(offset.at("x").get<double>(), offset.at("y").get<double>(), offset.at("z").get<double>());
        if (!off.allFinite()) throw std::runtime_error("Non-finite PrintFins offset.");
        const Transform3d inverse = object.instances.front()->get_matrix().inverse();
        // Prepare a detached copy with backups disabled. No project mutation until
        // final insertion: validation errors also leave the undo history untouched.
        Model scratch;
        ModelObject &prepared = *scratch.add_object(object);
        const size_t original_volumes = object.volumes.size();
        std::vector<bool> used(triangles.size() / 9, false);
        TriangleMesh fin_geometry;
        for (const auto &piece : result.at("pieces")) {
            indexed_triangle_set its;
            for (const auto &range : piece.at("ranges")) {
                if (range.size() != 2) throw std::runtime_error("Invalid PrintFins piece range.");
                const size_t begin = range.at(0).get<size_t>(), end = range.at(1).get<size_t>();
                if (begin >= end || end > used.size()) throw std::runtime_error("Invalid PrintFins piece range.");
                for (size_t t = begin; t < end; ++t) {
                    if (used[t]) throw std::runtime_error("Overlapping PrintFins piece ranges.");
                    used[t] = true;
                    const int start = int(its.vertices.size());
                    for (int k = 0; k < 3; ++k) {
                        const size_t i = 9 * t + 3 * k;
                        const Vec3d world(triangles[i], triangles[i + 1], triangles[i + 2]);
                        const Vec3f local = (inverse * (world - off)).cast<float>();
                        if (!world.allFinite() || !local.allFinite()) throw std::runtime_error("Non-finite PrintFins vertex.");
                        its.vertices.push_back(local);
                    }
                    its.indices.emplace_back(start, start + (inverse.linear().determinant() < 0 ? 2 : 1),
                                             start + (inverse.linear().determinant() < 0 ? 1 : 2));
                }
            }
            if (its.indices.empty()) throw std::runtime_error("Empty PrintFins piece.");
            its_merge_vertices(its);
            TriangleMesh mesh(std::move(its));
            TriangleMesh posed = mesh;
            posed.transform(object.instances.front()->get_matrix(), true);
            fin_geometry.merge(posed);
            auto *volume = prepared.add_volume(std::move(mesh), ModelVolumeType::MODEL_PART, false);
            volume->name = "PrintFins " + piece.at("kind").get<std::string>() + " " + piece.at("id").get<std::string>();
            volume->calculate_convex_hull();
        }
        if (std::find(used.begin(), used.end(), false) != used.end())
            throw std::runtime_error("PrintFins pieces do not cover the output.");
        const double height = m_request["options"]["layerHeight"].get<double>();
        const double first = m_request["options"]["firstLayerHeight"].get<double>();
        const double top = fin_geometry.bounding_box().max.z();
        if (!std::isfinite(top) || top / height > 100000)
            throw std::runtime_error("PrintFins geometry exceeds the layer validation limit.");
        std::vector<float> planes{float(first / 2)};
        for (double z = first + height / 2; z < top; z += height) planes.push_back(float(z));
        const auto slices = slice_mesh(fin_geometry.its, planes, MeshSlicingParams{});
        if (std::none_of(slices.begin(), slices.end(), [](const auto &layer) { return !layer.empty(); }))
            throw std::runtime_error("PrintFins geometry produced no slice contours.");
        prepared.invalidate_bounding_box();
        prepared.ensure_on_bed(true);
        if (!prepared.instances.front()->get_matrix().matrix().isApprox(object.instances.front()->get_matrix().matrix(), 1e-9))
            throw std::runtime_error("Adding PrintFins would move the model; result discarded.");

        m_plater.take_snapshot("Generate PrintFins");
        // Use Bambu's normal volume-copy path (meshes/hulls are shared), keeping
        // the original parts, settings and instance. One undo restores the input.
        try {
            for (size_t i = original_volumes; i < prepared.volumes.size(); ++i)
                object.add_volume(*prepared.volumes[i]);
            object.invalidate_bounding_box();
            wxGetApp().obj_list()->add_volumes_to_object_in_list(m_object_index);
            m_plater.changed_object(object);
            Slic3r::save_object_mesh(object);
        } catch (...) {
            m_plater.undo();
            throw;
        }
        m_finished = true;
        m_timeout.Stop();
        EndModal(wxID_OK);
    }

public:
    PrintFinsDialog(Plater &plater, int index) :
        wxDialog(&plater, wxID_ANY, "PrintFins", wxDefaultPosition, wxSize(760, 780), wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER),
        m_plater(plater), m_object_index(index), m_timeout(this)
    {
        const auto &object = *plater.model().objects[index];
        m_object_id = object.id();
        m_request = {{"positions", posed_mesh(object)}, {"options", layer_heights(plater, object)}};
        auto *layout = new wxBoxSizer(wxVERTICAL);
        m_status = new wxStaticText(this, wxID_ANY, "Loading PrintFins settings...");
        layout->Add(m_status, 0, wxALL | wxEXPAND, 12);
        SetSizer(layout);
        Bind(wxEVT_BUTTON, [this](wxCommandEvent &) { cancel(); }, wxID_CANCEL);
        Bind(wxEVT_CLOSE_WINDOW, [this](wxCloseEvent &) { cancel(); });
        Bind(wxEVT_TIMER, [this](wxTimerEvent &) {
            fail(m_busy ? "PrintFins engine timed out after 120 seconds. Close and try a simpler model."
                        : "PrintFins settings could not be loaded. Check the WebView2 runtime and local resources.");
        });
#if defined(_WIN32) && wxUSE_WEBVIEW_EDGE
        m_web = WebView::CreateWebView(this, "about:blank", "PrintFins");
        if (m_web) {
            layout->Add(m_web, 1, wxEXPAND | wxLEFT | wxRIGHT, 12);
            m_web->Bind(wxEVT_WEBVIEW_NAVIGATING, [](wxWebViewEvent &e) {
                if (e.GetURL() != "about:blank" && e.GetURL() != "https://printfins-poc.invalid/tool.html") e.Veto();
            });
            m_web->Bind(wxEVT_WEBVIEW_NEWWINDOW, [](wxWebViewEvent &e) { e.Veto(); });
            m_web->Bind(wxEVT_WEBVIEW_ERROR, [this](wxWebViewEvent &) { fail("Cannot load the local PrintFins settings page."); });
            m_web->Bind(wxEVT_WEBVIEW_LOADED, [this](wxWebViewEvent &) {
                if (m_mapped || m_finished) return;
                try {
                    auto *backend = static_cast<ICoreWebView2 *>(m_web->GetNativeBackend());
                    Microsoft::WRL::ComPtr<ICoreWebView2_3> local;
                    if (!backend || FAILED(backend->QueryInterface(IID_PPV_ARGS(&local))))
                        throw std::runtime_error("WebView2 virtual host mapping is unavailable.");
                    const wxString assets = wxString::FromUTF8(resources_dir() + "/printfins");
                    if (FAILED(local->SetVirtualHostNameToFolderMapping(L"printfins-poc.invalid", assets.wc_str(), COREWEBVIEW2_HOST_RESOURCE_ACCESS_KIND_DENY)))
                        throw std::runtime_error("Cannot map local PrintFins resources.");
                    m_mapped = true;
                    m_web->LoadURL("https://printfins-poc.invalid/tool.html");
                } catch (const std::exception &e) { fail(e.what()); }
            });
            m_web->Bind(wxEVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, [this](wxWebViewEvent &event) {
                if (m_finished) return;
                try {
                    const auto message = Json::parse(event.GetString().ToStdString());
                    const auto action = message.value("action", "");
                    if (action == "cancel") {
                        cancel();
                    } else if (action == "ready" && !m_ready) {
                        m_ready = true;
                        m_timeout.Stop();
                        if (!WebView::RunScript(m_web, wxString::FromUTF8("window.initPrintFins(" + m_request.dump() + ");")))
                            throw std::runtime_error("Cannot initialize PrintFins settings.");
                        m_status->SetLabel("Generate fins for the selected model, or cancel to leave the project unchanged.");
                        m_status->Wrap(700);
                        Layout();
                    } else if (action == "computing" && m_ready && !m_busy) {
                        m_busy = true;
                        m_status->SetLabel("Generating PrintFins... Cancel remains available.");
                        m_timeout.StartOnce(120000);
                    } else if (action == "error") {
                        throw std::runtime_error(message.value("error", "PrintFins page failed."));
                    } else if (action == "result" && m_busy) {
                        m_timeout.Stop();
                        accept(message);
                    }
                } catch (const std::exception &e) { fail(e.what()); }
            });
            m_web->LoadURL("about:blank");
            m_timeout.StartOnce(30000);
        } else {
            CallAfter([this] { fail("Cannot create PrintFins WebView2. Check that WebView2 is installed."); });
        }
#else
        CallAfter([this] { fail("PrintFins currently requires Windows with WebView2."); });
#endif
        layout->Add(CreateButtonSizer(wxCANCEL), 0, wxALL | wxALIGN_RIGHT, 12);
        SetMinSize(wxSize(540, 460));
        CentreOnParent();
    }
};
} // namespace

void show_printfins_tool(Plater &plater)
{
    try {
        if (!plater.can_do_ui_job() || !plater.can_add_model() || plater.printer_technology() != ptFFF)
            throw std::runtime_error("Finish the current operation and use the Prepare view with an FFF printer before opening PrintFins.");
        PrintFinsDialog dialog(plater, selected_object(plater));
        dialog.ShowModal();
    } catch (const std::exception &e) {
        wxMessageBox(wxString::FromUTF8(e.what()), "PrintFins", wxOK | wxICON_INFORMATION, &plater);
    }
}
} // namespace Slic3r::GUI
