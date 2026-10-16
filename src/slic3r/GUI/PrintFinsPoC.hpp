#ifndef slic3r_GUI_PrintFinsPoC_hpp_
#define slic3r_GUI_PrintFinsPoC_hpp_
namespace Slic3r::GUI {
class Plater;
// Modal tool; only a successfully validated result changes the selected object.
void show_printfins_tool(Plater &plater);
}
#endif
