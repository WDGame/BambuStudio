#ifndef slic3r_GUI_PrintFinsPoC_hpp_
#define slic3r_GUI_PrintFinsPoC_hpp_
#include <functional>
#include <string>
class wxWindow;
namespace Slic3r { class DynamicPrintConfig; }
namespace Slic3r::GUI {
class Plater;
// Modal tool; only a successfully validated result changes the selected object.
void show_printfins_tool(Plater &plater);
// Native Support-page controls. Settings use Bambu's normal dynamic config path.
wxWindow *create_printfins_settings(wxWindow *parent,
    std::function<const DynamicPrintConfig &()> config,
    std::function<DynamicPrintConfig()> preset,
    std::function<void(const std::string &)> save);
void refresh_printfins_settings(wxWindow *panel);
}
#endif
