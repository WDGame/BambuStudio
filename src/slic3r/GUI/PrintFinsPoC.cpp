#include "PrintFinsPoC.hpp"
#include "PrintFinsSettings.hpp"
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
#include <array>
#include <cmath>
#include <fstream>
#include <wx/checkbox.h>
#include <wx/choice.h>
#include <wx/panel.h>
#include <wx/textctrl.h>
#include "Widgets/Button.hpp"
#include "Widgets/TextInput.hpp"
#include "Field.hpp"
#include "libslic3r/LocalesUtils.hpp"
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

Json localized_settings_schema(Json schema)
{
    for (auto &spec : schema.at("options")) {
        const std::string key = spec.at("key").get<std::string>();
        auto set = [&spec](const char *field, const std::string &value) { spec[field] = value; };
        if (key == "mode") {
            set("label", _u8L("Generation mode"));
            set("tooltip", _u8L("Auto places fins automatically. Full Coverage adds original fill walls under overhangs left by Auto. Wide-face coverage controls density separately."));
            spec["choices"][0]["label"] = _u8L("Auto");
            spec["choices"][1]["label"] = _u8L("Full Coverage");
        } else if (key == "threshold") {
            set("label", _u8L("Overhang"));
            set("tooltip", _u8L("Surface angle from the plate below which a face needs support."));
        } else if (key == "tines") {
            set("label", _u8L("Tines"));
            set("hint", _u8L("grip the part"));
            set("tooltip", _u8L("Tines fuse the support to the part so it grips instead of just propping. Off = plain breakaway wall."));
        } else if (key == "tineDensity") {
            set("label", _u8L("Tine grip"));
            set("hint", _u8L("light ⟶ firm"));
            set("tooltip", _u8L("How tightly to space the grip tines. Light = fewest marks (default), a per-wall floor keeps grip; Firm = dense comb / max grip for a tippy or tall part."));
        } else if (key == "gap") {
            set("label", _u8L("Support gap"));
            set("tooltip", _u8L("Clearance between a support top and the part. Bigger = cleaner surface / easier removal; too big stops holding the overhang. Default 0.2mm."));
        } else if (key == "padStyle") {
            set("label", _u8L("Bed pad"));
            set("tooltip", _u8L("A tilted part rests on an edge and peels off the plate without a pad. Auto: Light, or Sure hold when the part meets the plate on a point or a small round foot. Light: one layer, 0.12mm off the part, peels off like a brim. Sure hold: thicker and tacked into the part, holds harder but is harder to remove."));
            const std::array<std::string, 4> labels{_u8L("Off"), _u8L("Auto"), _u8L("Light"), _u8L("Sure hold")};
            for (size_t i = 0; i < labels.size(); ++i) spec["choices"][i]["label"] = labels[i];
        } else if (key == "sway.on") {
            set("label", _u8L("Sway braces"));
            set("hint", _u8L("tall parts"));
            set("tooltip", _u8L("Stand tapered buttress ribs against the upright sides of a tall part, tied on with tines all the way up, so it doesn't drift or wobble as it grows."));
        } else if (key == "sway.gripFrom") {
            set("label", _u8L("Brace grip from"));
            set("hint", _u8L("mm up"));
            set("tooltip", _u8L("Height the brace tines start at. 0 = grip the whole height; raise it to tie on only above where the part starts to move."));
        } else if (key == "sway.tineSpacing") {
            set("label", _u8L("Brace tine spacing"));
            set("tooltip", _u8L("Vertical distance between brace tines. Smaller = held tighter, more marks on the side. Default 6mm."));
        } else if (key == "sway.reach") {
            set("label", _u8L("Brace depth"));
            set("hint", _u8L("% of height"));
            set("tooltip", _u8L("How far the brace reaches out at the bed, as a share of its height. Deeper = stiffer, more plastic. Default 15%."));
        } else if (key == "cutout") {
            set("label", _u8L("Cutouts"));
            set("tooltip", _u8L("Cut holes through tall breakaway walls to save filament. The top edge that holds the part, the foot, and the wall's ends stay solid, and every hole has a pointed roof so it prints without bridging. Short walls stay solid."));
            const std::array<std::string, 5> labels{_u8L("None"), _u8L("Diamond"), _u8L("Triangle"), _u8L("Arch"), _u8L("Lattice")};
            for (size_t i = 0; i < labels.size(); ++i) spec["choices"][i]["label"] = labels[i];
        } else if (key == "coverage") {
            set("label", _u8L("Wide-face coverage"));
            set("hint", _u8L("sparse ⟶ dense"));
            set("tooltip", _u8L("How densely to line a WIDE overhang face with fins. The middle is the anti-sag default; drag LEFT for fewer fins (a small part can go down to one — the readout warns if a broad face then risks sagging), RIGHT for more support. Narrow parts are unaffected."));
        } else if (key == "plateOnly") {
            set("label", _u8L("Plate only"));
            set("tooltip", _u8L("Stand every support on the build plate, never on the part itself. An overhang with part under it is left unsupported, and the readout says how many."));
        }
    }
    return schema;
}

int selected_object(Plater &plater)
{
    const auto &selection = plater.get_selection();
    const int index = selection.get_object_idx();
    if ((!selection.is_single_full_instance() && !selection.is_single_full_object()) ||
        index < 0 || size_t(index) >= plater.model().objects.size())
        throw std::runtime_error(_u8L("Select one complete model on the plate before using PrintFins."));
    return index;
}

Json layer_heights(Plater &plater, const ModelObject &object)
{
    auto config = *plater.config();
    config.apply(object.config.get());
    const double height = config.option<ConfigOptionFloat>("layer_height")->value;
    const double first = config.option<ConfigOptionFloat>("initial_layer_print_height")->value;
    if (!std::isfinite(height) || height <= 0 || !std::isfinite(first) || first <= 0)
        throw std::runtime_error(_u8L("PrintFins requires positive, constant layer heights."));
    return {{"layerHeight", height}, {"firstLayerHeight", first}};
}

Json posed_mesh(const ModelObject &object)
{
    if (object.instances.size() != 1 || object.volumes.empty())
        throw std::runtime_error(_u8L("PrintFins supports one instance of a model with plain model parts."));
    if (!object.layer_height_profile.empty() || !object.layer_config_ranges.empty())
        throw std::runtime_error(_u8L("Variable layer heights and height range modifiers are not supported by PrintFins."));
    Json positions = Json::array();
    for (const ModelVolume *volume : object.volumes) {
        if (volume->name.rfind("PrintFins ", 0) == 0)
            throw std::runtime_error(_u8L("This model already contains PrintFins. Undo or remove those parts explicitly before generating again."));
        if (!volume->is_model_part())
            throw std::runtime_error(_u8L("PrintFins does not support modifiers or negative/support volumes."));
        const Transform3d matrix = object.instances.front()->get_matrix() * volume->get_matrix();
        if (!matrix.matrix().allFinite() || std::abs(matrix.linear().determinant()) < 1e-12)
            throw std::runtime_error("The model has an invalid or singular transform.");
        const auto &its = volume->mesh().its;
        if (its.indices.size() > (900000 - positions.size()) / 9)
            throw std::runtime_error(_u8L("PrintFins currently supports at most 100000 input triangles."));
        for (const auto &face : its.indices) {
            for (int k = 0; k < 3; ++k) {
                const int corner = matrix.linear().determinant() < 0 && k > 0 ? 3 - k : k;
                const Vec3d p = matrix * its.vertices[face[corner]].cast<double>();
                if (!p.allFinite()) throw std::runtime_error("The model contains non-finite vertices.");
                for (int axis = 0; axis < 3; ++axis) positions.push_back(p[axis]);
            }
        }
    }
    if (positions.empty()) throw std::runtime_error(_u8L("The selected model has no triangles."));
    return positions;
}

class PrintFinsDialog final : public wxDialog {
    Plater &m_plater;
    int m_object_index;
    Json m_request;
    Json m_layer_heights;
    bool m_native;
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
        if (posed_mesh(object) != m_request["positions"] || layer_heights(m_plater, object) != m_layer_heights)
            throw std::runtime_error("Model or layer settings changed; PrintFins result discarded.");
        const auto triangles = result.at("triangles").get<std::vector<double>>();
        if (triangles.size() % 9 || triangles.size() > 9000000)
            throw std::runtime_error("PrintFins returned invalid or oversized geometry.");
        if (triangles.empty()) {
            m_finished = true;
            m_timeout.Stop();
            wxMessageBox(_L("PrintFins generated no geometry for this model and these settings. The project is unchanged."),
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
            volume->config.set_key_value("make_overhang_printable", new ConfigOptionBool(false));
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

        m_plater.take_snapshot(_u8L("Generate PrintFins"));
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
        BOOST_LOG_TRIVIAL(info) << "PrintFins accepted " << (prepared.volumes.size() - original_volumes) << " new model volumes.";
        EndModal(wxID_OK);
    }

public:
    PrintFinsDialog(Plater &plater, int index, const Json *options = nullptr) :
        wxDialog(&plater, wxID_ANY, "PrintFins", wxDefaultPosition, wxSize(760, 780), wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER),
        m_plater(plater), m_object_index(index), m_native(options != nullptr), m_timeout(this)
    {
        const auto &object = *plater.model().objects[index];
        m_object_id = object.id();
        m_layer_heights = layer_heights(plater, object);
        Json values = options ? *options : Json::object();
        values.update(m_layer_heights); // Actual slicer heights always win.
        m_request = {{"positions", posed_mesh(object)}, {"options", values},
                     {"uiLocale", into_u8(wxGetApp().current_language_code_safe())}};
        auto *layout = new wxBoxSizer(wxVERTICAL);
        m_status = new wxStaticText(this, wxID_ANY, _L("Loading PrintFins settings..."));
        layout->Add(m_status, 0, wxALL | wxEXPAND, 12);
        SetSizer(layout);
        Bind(wxEVT_BUTTON, [this](wxCommandEvent &) { cancel(); }, wxID_CANCEL);
        Bind(wxEVT_CLOSE_WINDOW, [this](wxCloseEvent &) { cancel(); });
        Bind(wxEVT_TIMER, [this](wxTimerEvent &) {
            fail(m_busy ? _u8L("PrintFins engine timed out after 120 seconds. Close and try a simpler model.")
                        : _u8L("PrintFins settings could not be loaded. Check the WebView2 runtime and local resources."));
        });
#if defined(_WIN32) && wxUSE_WEBVIEW_EDGE
        m_web = WebView::CreateWebView(this, "about:blank", "PrintFins");
        if (m_web) {
            if (m_native) m_web->Hide();
            else layout->Add(m_web, 1, wxEXPAND | wxLEFT | wxRIGHT, 12);
            m_web->Bind(wxEVT_WEBVIEW_NAVIGATING, [](wxWebViewEvent &e) {
                if (e.GetURL() != "about:blank" && e.GetURL() != "https://printfins-poc.invalid/tool.html") e.Veto();
            });
            m_web->Bind(wxEVT_WEBVIEW_NEWWINDOW, [](wxWebViewEvent &e) { e.Veto(); });
            m_web->Bind(wxEVT_WEBVIEW_ERROR, [this](wxWebViewEvent &event) {
                BOOST_LOG_TRIVIAL(error) << "PrintFins WebView: url=" << event.GetURL().ToStdString()
                    << " code=" << event.GetInt() << " description=" << event.GetString().ToStdString()
                    << " mapped=" << m_mapped << " ready=" << m_ready;
                fail(_u8L("Cannot load the local PrintFins settings page."));
            });
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
                    BOOST_LOG_TRIVIAL(info) << "PrintFins mapped local resources; loading tool page.";
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
                        BOOST_LOG_TRIVIAL(info) << "PrintFins page ready.";
                        m_ready = true;
                        m_timeout.Stop();
                        const std::string script = "window.initPrintFins(" + m_request.dump() + ");" +
                            (m_native ? "document.getElementById('generate').click();" : "");
                        if (!WebView::RunScript(m_web, wxString::FromUTF8(script)))
                            throw std::runtime_error("Cannot initialize PrintFins settings.");
                        if (!m_native) m_status->SetLabel(_L("Generate fins for the selected model, or cancel to leave the project unchanged."));
                        m_status->Wrap(700);
                        Layout();
                    } else if (action == "computing" && m_ready && !m_busy) {
                        BOOST_LOG_TRIVIAL(info) << "PrintFins worker computing.";
                        m_busy = true;
                        m_status->SetLabel(_L("Generating PrintFins... Cancel remains available."));
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
            CallAfter([this] { fail(_u8L("Cannot create PrintFins WebView2. Check that WebView2 is installed.")); });
        }
#else
        CallAfter([this] { fail(_u8L("PrintFins currently requires Windows with WebView2.")); });
#endif
        layout->Add(CreateButtonSizer(wxCANCEL), 0, wxALL | wxALIGN_RIGHT, 12);
        SetMinSize(m_native ? wxSize(540, 160) : wxSize(540, 460));
        if (m_native) SetSize(wxSize(580, 180));
        CentreOnParent();
    }
};

// The schema is read from the verified upstream snapshot, never copied defaults.
Json settings_schema()
{
    std::ifstream stream(resources_dir() + "/printfins/vendor/plugins/shared/engine/options.json");
    if (!stream) throw std::runtime_error(_u8L("Cannot read the original PrintFins options schema."));
    return Json::parse(stream);
}

bool setting_condition(const Json &condition, const Json &values)
{
    if (condition.is_string()) return values.at(condition.get<std::string>()).get<bool>();
    if (condition.contains("any")) {
        for (const auto &item : condition["any"]) if (setting_condition(item, values)) return true;
        return false;
    }
    const auto &value = values.at(condition.at("key").get<std::string>());
    for (const auto &choice : condition.at("in")) if (choice == value) return true;
    return false;
}

class NativePrintFinsSettings final : public wxPanel {
    struct Control { Json spec; wxWindow *input; wxSizer *row; ScalableButton *reset; };
    std::vector<Control> m_controls;
    Json m_schema;
    std::function<const DynamicPrintConfig &()> m_config;
    std::function<DynamicPrintConfig()> m_preset;
    std::function<void(const std::string &)> m_save;
    wxStaticText *m_status;
    Button *m_generate;
    std::string m_loaded;

    Json read() const
    {
        Json values = Json::object();
        for (const auto &control : m_controls)
            values[control.spec.at("key").get<std::string>()] = control.spec.at("default");
        for (const auto &control : m_controls) {
            const auto key = control.spec.at("key").get<std::string>();
            bool visible = true;
            for (const auto &condition : control.spec.value("showIf", Json::array()))
                visible = visible && setting_condition(condition, values);
            // Like the original dialog, hidden fields cannot block submission.
            if (!visible) { values.erase(key); continue; }
            if (auto *check = dynamic_cast<wxCheckBox *>(control.input)) values[key] = check->GetValue();
            else if (auto *number = dynamic_cast<::TextInput *>(control.input)) {
                auto *text = number->GetTextCtrl();
                wxString entry = text->GetValue();
                const char separator = is_decimal_separator_point() ? '.' : ',';
                if (entry.Replace(separator == '.' ? ',' : '.', separator, false)) text->ChangeValue(entry);
                double displayed;
                const bool in_range = number->CheckValid(false);
                if (!entry.ToDouble(&displayed) || !std::isfinite(displayed))
                    throw std::runtime_error(_u8L("Enter a finite number for PrintFins: ") + key);
                if (!in_range) throw std::runtime_error(_u8L("PrintFins setting outside the allowed range: ") + key);
                const double value = displayed / (control.spec.value("percent", false) ? 100. : 1.);
                PrintFinsSettings::validate(control.spec, value);
                values[key] = value;
            }
            else {
                const int choice = static_cast<wxChoice *>(control.input)->GetSelection();
                if (choice < 0) throw std::runtime_error(_u8L("Choose a valid PrintFins setting."));
                values[key] = control.spec.at("choices").at(choice).at("value");
            }
        }
        return values;
    }

    void commit()
    {
        try {
            const auto visible = read();
            const auto previous = PrintFinsSettings::values(m_schema, m_config());
            auto updated = previous;
            updated.update(visible); // Keep hidden settings when tines/braces are disabled.
            dependencies(updated);
            if (updated != previous) m_save(PrintFinsSettings::serialize(m_schema, updated, m_preset()));
            refresh();
        } catch (const std::exception &error) { m_status->SetLabel(wxString::FromUTF8(error.what())); }
    }

    void dependencies(const Json &values)
    {
        for (const auto &control : m_controls) {
            bool visible = true;
            for (const auto &condition : control.spec.value("showIf", Json::array()))
                visible = visible && setting_condition(condition, values);
            GetSizer()->Show(control.row, visible, true);
        }
        Layout();
        GetParent()->Layout();
    }

public:
    // Bambu group visibility updates must not reveal this panel for other types.
    bool Show(bool show = true) override
    {
        return wxPanel::Show(show && m_config().opt_enum<SupportType>("support_type") == stPrintFins);
    }

    NativePrintFinsSettings(wxWindow *parent, std::function<const DynamicPrintConfig &()> config,
                           std::function<DynamicPrintConfig()> preset,
                           std::function<void(const std::string &)> save) :
        wxPanel(parent), m_schema(localized_settings_schema(PrintFinsSettings::native_schema(settings_schema()))),
        m_config(std::move(config)), m_preset(std::move(preset)), m_save(std::move(save))
    {
        auto *layout = new wxBoxSizer(wxVERTICAL);
        SetSizer(layout);
        for (const auto &spec : m_schema.at("options")) {
            if (spec.contains("hostSupplied")) continue;
            auto *row = new wxBoxSizer(wxHORIZONTAL);
            auto *label = new wxStaticText(this, wxID_ANY, wxString::FromUTF8(spec.at("label").get<std::string>()));
            row->Add(label, 1, wxALIGN_CENTER_VERTICAL | wxRIGHT, FromDIP(8));
            wxWindow *input;
            const auto type = spec.at("type").get<std::string>();
            if (type == "bool") input = new wxCheckBox(this, wxID_ANY, "");
            else if (type == "number") {
                const double scale = spec.value("percent", false) ? 100. : 1.;
                const auto key = spec.at("key").get<std::string>();
                const wxString unit = spec.value("percent", false) ? "%" : key == "threshold" ? wxString::FromUTF8("\xc2\xb0") : "mm";
                auto *number = new ::TextInput(this, double_to_string(spec.at("default").get<double>() * scale, 12),
                    unit, "", wxDefaultPosition, wxSize(FromDIP(100), -1), wxTE_PROCESS_ENTER);
                number->SetValCheckers({TextInputValChecker::CreateDoubleRangeChecker(
                    spec.at("min").get<double>() * scale, spec.at("max").get<double>() * scale, false)});
                wxGetApp().UpdateDarkUI(number);
                input = number;
            } else {
                auto *choice = new wxChoice(this, wxID_ANY);
                for (const auto &item : spec.at("choices")) choice->Append(wxString::FromUTF8(item.at("label").get<std::string>()));
                input = choice;
            }
            input->SetToolTip(wxString::FromUTF8(spec.value("tooltip", "")));
            row->Add(input, 0, wxALIGN_CENTER_VERTICAL);
            if (auto *number = dynamic_cast<::TextInput *>(input)) {
                auto advance = [this, number, spec](int direction) {
                    try {
                        wxString entry = number->GetTextCtrl()->GetValue();
                        const char separator = is_decimal_separator_point() ? '.' : ',';
                        entry.Replace(separator == '.' ? ',' : '.', separator, false);
                        double displayed;
                        if (!entry.ToDouble(&displayed)) throw std::runtime_error(_u8L("Enter a valid PrintFins number."));
                        const double scale = spec.value("percent", false) ? 100. : 1.;
                        number->GetTextCtrl()->ChangeValue(double_to_string(
                            PrintFinsSettings::step(spec, displayed / scale, direction) * scale, 12));
                        commit();
                    } catch (const std::exception &error) { m_status->SetLabel(wxString::FromUTF8(error.what())); }
                };
                auto *arrows = new wxBoxSizer(wxVERTICAL);
                for (int direction : {1, -1}) {
                    auto *button = new Button(this, "", direction > 0 ? "spin_inc" : "spin_dec", wxBORDER_NONE, 6);
                    button->SetPaddingSize(wxSize(FromDIP(3), 0));
                    button->DisableFocusFromKeyboard();
                    button->Bind(wxEVT_BUTTON, [advance, direction](wxCommandEvent &) { advance(direction); });
                    arrows->Add(button, 0);
                }
                row->Add(arrows, 0, wxALIGN_CENTER_VERTICAL);
                number->GetTextCtrl()->Bind(wxEVT_KEY_DOWN, [advance](wxKeyEvent &event) {
                    if (event.GetKeyCode() == WXK_UP) advance(1);
                    else if (event.GetKeyCode() == WXK_DOWN) advance(-1);
                    else event.Skip();
                });
            }
            const auto hint = spec.value("hint", "");
            if (!hint.empty() && type != "number") row->Add(new wxStaticText(this, wxID_ANY, wxString::FromUTF8(hint)),
                                       0, wxALIGN_CENTER_VERTICAL | wxLEFT, FromDIP(5));
            auto *reset = new ScalableButton(this, wxID_ANY, "undo");
            reset->SetToolTip(_L("Click to drop current modify and reset to saved value."));
            const auto key = spec.at("key").get<std::string>();
            reset->Bind(wxEVT_BUTTON, [this, key](wxCommandEvent &) {
                try {
                    const auto preset = m_preset();
                    m_save(PrintFinsSettings::serialize(m_schema,
                        PrintFinsSettings::reset(m_schema, m_config(), preset, key), preset));
                    refresh();
                } catch (const std::exception &error) { m_status->SetLabel(wxString::FromUTF8(error.what())); }
            });
            row->Add(reset, 0, wxALIGN_CENTER_VERTICAL | wxLEFT, FromDIP(5));
            layout->Add(row, 0, wxEXPAND | wxBOTTOM, FromDIP(5));
            m_controls.push_back({spec, input, row, reset});
        }
        m_status = new wxStaticText(this, wxID_ANY, "");
        layout->Add(m_status, 0, wxEXPAND | wxTOP | wxBOTTOM, FromDIP(6));
        m_generate = new Button(this, _L("Generate PrintFins (Auto)"));
        layout->Add(m_generate, 0, wxALIGN_RIGHT);
        auto edited = [this](wxCommandEvent &) {
            commit();
        };
        Bind(wxEVT_CHECKBOX, edited);
        Bind(wxEVT_CHOICE, edited);
        // Enter/focus commit typed numeric values through the same native event.
        for (const auto &control : m_controls) if (auto *number = dynamic_cast<::TextInput *>(control.input)) {
            // TextInput forwards Enter with ProcessEventLocally(), not to its parent.
            number->Bind(wxEVT_TEXT_ENTER, edited);
            number->GetTextCtrl()->Bind(wxEVT_KILL_FOCUS, [this, edited](wxFocusEvent &event) mutable {
                wxCommandEvent changed; edited(changed); event.Skip();
            });
        }
        m_generate->Bind(wxEVT_BUTTON, [this](wxCommandEvent &) {
            try {
                auto &plater = *wxGetApp().plater();
                if (!plater.can_do_ui_job() || !plater.can_add_model() || plater.printer_technology() != ptFFF)
                    throw std::runtime_error(_u8L("Finish the current operation and select one complete model in Prepare."));
                const int index = selected_object(plater);
                auto effective = m_config();
                effective.apply(plater.model().objects[index]->config.get());
                if (effective.opt_enum<SupportType>("support_type") != stPrintFins || !effective.opt_bool("enable_support"))
                    throw std::runtime_error(_u8L("Enable the PrintFins support type for the selected model first."));
                if (effective.opt_bool("make_overhang_printable"))
                    throw std::runtime_error(_u8L("Disable Make overhangs printable before generating PrintFins."));
                if (effective.opt_int("raft_layers") != 0)
                    throw std::runtime_error(_u8L("Set Bambu raft layers to zero before generating PrintFins."));
                const Json values = read();
                const auto *stored = effective.option<ConfigOptionString>("printfins_options");
                if (stored) {
                    const auto saved = Json::parse(stored->value);
                    for (auto it = saved.begin(); it != saved.end(); ++it) {
                        if (std::none_of(m_controls.begin(), m_controls.end(), [&](const auto &control) { return control.spec.at("key") == it.key(); }))
                            throw std::runtime_error(_u8L("Unknown PrintFins setting: ") + it.key());
                        if (values.contains(it.key()) && values.at(it.key()) != it.value())
                            throw std::runtime_error(_u8L("The selected model has different PrintFins overrides. Open its object settings before generating."));
                    }
                }
                PrintFinsDialog dialog(plater, index, &values);
                dialog.ShowModal();
            } catch (const std::exception &error) {
                wxMessageBox(wxString::FromUTF8(error.what()), "PrintFins", wxOK | wxICON_INFORMATION, this);
            }
        });
        wxGetApp().UpdateDarkUI(this);
        refresh();
    }

    void refresh()
    {
        const auto &config = m_config();
        const bool visible = config.opt_enum<SupportType>("support_type") == stPrintFins;
        if (Show(visible)) GetParent()->Layout();
        if (!visible) return;
        try {
            const auto *option = config.option<ConfigOptionString>("printfins_options");
            const std::string stored = option ? option->value : "{}";
            if (stored != m_loaded) {
                const auto saved = PrintFinsSettings::values(m_schema, config);
                for (const auto &control : m_controls) {
                    const auto key = control.spec.at("key").get<std::string>();
                    const auto value = saved.value(key, control.spec.at("default"));
                    if (auto *check = dynamic_cast<wxCheckBox *>(control.input)) check->SetValue(value.get<bool>());
                    else if (auto *number = dynamic_cast<::TextInput *>(control.input)) {
                        const double v = value.get<double>();
                        number->GetTextCtrl()->ChangeValue(double_to_string(v * (control.spec.value("percent", false) ? 100. : 1.), 12));
                    } else {
                        int selected = wxNOT_FOUND, index = 0;
                        for (const auto &choice : control.spec.at("choices")) {
                            if (choice.at("value") == value) selected = index;
                            ++index;
                        }
                        if (selected == wxNOT_FOUND) throw std::runtime_error(_u8L("Invalid PrintFins choice: ") + key);
                        static_cast<wxChoice *>(control.input)->SetSelection(selected);
                    }
                }
                m_loaded = stored;
                dependencies(read());
            }
            const auto current = PrintFinsSettings::values(m_schema, config);
            const auto baseline = PrintFinsSettings::values(m_schema, m_preset());
            for (const auto &control : m_controls) {
                const auto key = control.spec.at("key").get<std::string>();
                const bool changed = current.at(key) != baseline.at(key);
                control.reset->SetBitmap_(changed ? "undo" : "dot");
                control.reset->Enable(changed);
            }
            m_generate->Enable(config.opt_bool("enable_support"));
            const bool full = current.at("mode") == "full";
            m_generate->SetLabel(full ? _L("Generate PrintFins (Full Coverage)") : _L("Generate PrintFins (Auto)"));
            m_status->SetLabel(full
                ? _L("Full Coverage: add original fill walls under overhangs left by Auto. Wide-face coverage controls density separately.\nSelect one complete model and generate before slicing.")
                : _L("Auto: select one complete model. Layer heights come from Bambu Studio.\nGenerate before slicing; fins become ordinary printable parts."));
            m_status->Wrap(FromDIP(400));
            Layout();
            GetParent()->Layout();
        } catch (const std::exception &error) {
            m_generate->Disable();
            m_status->SetLabel(wxString::FromUTF8(error.what()));
        }
    }
};
} // namespace

wxWindow *create_printfins_settings(wxWindow *parent, std::function<const DynamicPrintConfig &()> config,
                                   std::function<DynamicPrintConfig()> preset,
                                   std::function<void(const std::string &)> save)
{
    try {
        return new NativePrintFinsSettings(parent, std::move(config), std::move(preset), std::move(save));
    } catch (const std::exception &error) {
        return new wxStaticText(parent, wxID_ANY, wxString::FromUTF8(error.what()));
    }
}

void refresh_printfins_settings(wxWindow *panel)
{
    if (auto *settings = dynamic_cast<NativePrintFinsSettings *>(panel)) settings->refresh();
}

void show_printfins_tool(Plater &plater)
{
    try {
        if (!plater.can_do_ui_job() || !plater.can_add_model() || plater.printer_technology() != ptFFF)
            throw std::runtime_error(_u8L("Finish the current operation and use the Prepare view with an FFF printer before opening PrintFins."));
        PrintFinsDialog dialog(plater, selected_object(plater));
        dialog.ShowModal();
    } catch (const std::exception &e) {
        wxMessageBox(wxString::FromUTF8(e.what()), "PrintFins", wxOK | wxICON_INFORMATION, &plater);
    }
}
} // namespace Slic3r::GUI
