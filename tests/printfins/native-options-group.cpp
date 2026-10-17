#include <catch2/catch.hpp>
#include "slic3r/GUI/OptionsGroup.hpp"
#include "slic3r/GUI/PrintFinsSettings.hpp"
#include "slic3r/GUI/Widgets/TextInput.hpp"
#include "libslic3r/Preset.hpp"
#include "libslic3r/LocalesUtils.hpp"
#include "libslic3r/Utils.hpp"
#include "libslic3r/Model.hpp"
#include "libslic3r/Format/bbs_3mf.hpp"
#include <boost/filesystem.hpp>
#include <fstream>
#include <limits>

using namespace Slic3r;
using namespace Slic3r::GUI;
namespace PF = Slic3r::GUI::PrintFinsSettings;

namespace {
PF::Json native_schema()
{
    std::ifstream stream(std::string(TEST_DATA_DIR) + "/../../resources/printfins/vendor/plugins/shared/engine/options.json");
    REQUIRE(stream.good());
    return PF::native_schema(PF::Json::parse(stream));
}
void set_options(DynamicPrintConfig &config, const PF::Json &values)
{
    config.set_key_value("printfins_options", new ConfigOptionString(values.dump()));
}
}

TEST_CASE("PrintFins native numeric limits and decimal arrow steps", "[PrintFins][Settings]")
{
    CNumericLocalesSetter numeric_locale;
    const auto schema = native_schema();
    struct Expected { const char *key; double min, max, initial, step; };
    for (const auto &expected : std::vector<Expected>{
        {"threshold",30,70,45,1}, {"tineDensity",0,1,0,0.01}, {"gap",0.1,0.4,0.2,0.01},
        {"coverage",0,1,0.5,0.01}, {"sway.gripFrom",0,2000,0,1},
        {"sway.tineSpacing",2,30,6,0.5}, {"sway.reach",0.05,0.5,0.15,0.01}}) {
        INFO(expected.key);
        const auto it = std::find_if(schema["options"].begin(), schema["options"].end(),
            [&](const auto &spec) { return spec.at("key") == expected.key; });
        REQUIRE(it != schema["options"].end());
        const auto &spec = *it;
        CHECK(spec.at("min").get<double>() == expected.min);
        CHECK(spec.at("max").get<double>() == expected.max);
        CHECK(spec.at("default").get<double>() == expected.initial);
        CHECK(spec.at("step").get<double>() == expected.step);
        const double scale = spec.value("percent", false) ? 100. : 1.;
        const auto checker = TextInputValChecker::CreateDoubleRangeChecker(expected.min * scale, expected.max * scale, false);
        CHECK(checker->CheckValid(wxString::FromDouble(expected.min * scale, 12)).empty());
        CHECK(checker->CheckValid(wxString::FromDouble(expected.max * scale, 12)).empty());
        CHECK(checker->CheckValid(wxString::FromDouble((expected.min + expected.step / 2) * scale, 12)).empty());
        CHECK_FALSE(checker->CheckValid(wxString::FromDouble((expected.min - 0.000001) * scale, 12)).empty());
        CHECK_FALSE(checker->CheckValid(wxString::FromDouble((expected.max + 0.000001) * scale, 12)).empty());
        CHECK_FALSE(checker->CheckValid("").empty());
        CHECK_FALSE(checker->CheckValid("bad").empty());
        CHECK_NOTHROW(PF::validate(spec, expected.min));
        CHECK_NOTHROW(PF::validate(spec, expected.max));
        CHECK_NOTHROW(PF::validate(spec, expected.min + expected.step / 2));
        CHECK_THROWS(PF::validate(spec, expected.min - 0.000001));
        CHECK_THROWS(PF::validate(spec, expected.max + 0.000001));
        CHECK_THROWS(PF::validate(spec, std::numeric_limits<double>::infinity()));
        CHECK_THROWS(PF::validate(spec, std::numeric_limits<double>::quiet_NaN()));
        CHECK_THROWS(PF::validate(spec, "bad"));
        CHECK_THROWS(PF::validate(spec, ""));
        CHECK_THROWS(PF::validate(spec, true));
        CHECK(PF::step(spec, expected.min, 1) == Approx(expected.min + expected.step));
        CHECK(PF::step(spec, expected.max, -1) == Approx(expected.max - expected.step));
        CHECK(PF::step(spec, expected.min, -1) == expected.min);
        CHECK(PF::step(spec, expected.max, 1) == expected.max);
        double value = expected.min;
        for (int i = 0; i < 10; ++i) value = PF::step(spec, value, 1);
        CHECK(value == Approx(expected.min + 10 * expected.step));
    }
}

TEST_CASE("PrintFins per-value reset follows selected saved preset and preserves other values", "[PrintFins][Preset]")
{
    const auto schema = native_schema();
    PresetCollection presets(Preset::TYPE_PRINT, Preset::print_options(),
        static_cast<const PrintRegionConfig &>(FullPrintConfig::defaults()));
    auto first = DynamicPrintConfig::full_print_config();
    set_options(first, {{"threshold",51}, {"tines",true}, {"tineDensity",0.21}, {"gap",0.31},
        {"padStyle","light"}, {"sway.on",true}, {"sway.gripFrom",31}, {"sway.tineSpacing",7.5},
        {"sway.reach",0.22}, {"cutout","arch"}, {"coverage",0.61}, {"plateOnly",true}});
    presets.load_preset("", "PrintFins A", first);
    REQUIRE(presets.get_selected_preset().config.has("printfins_options"));
    auto current = presets.get_edited_preset().config;
    auto changed = PF::values(schema, current);
    changed["gap"] = 0.23456789;
    changed["coverage"] = 0.77;
    changed.update(PF::Json{{"threshold",53}, {"tines",false}, {"tineDensity",0.37},
        {"padStyle","sure"}, {"sway.on",false}, {"sway.gripFrom",45}, {"sway.tineSpacing",8.5},
        {"sway.reach",0.26}, {"cutout","diamond"}, {"plateOnly",false}});
    set_options(current, changed);
    set_options(presets.get_edited_preset().config, changed);
    CHECK(presets.current_is_dirty());
    const auto saved_before = presets.get_selected_preset().config.opt_string("printfins_options");
    auto reset = PF::reset(schema, current, presets.get_selected_preset().config, "gap");
    CHECK(reset.at("gap") == 0.31);
    CHECK(reset.at("coverage") == 0.77);
    CHECK(reset.at("tineDensity") == 0.37); // hidden, not discarded
    CHECK(reset.at("tines") == false);
    CHECK(PF::values(schema, current).at("gap") == 0.23456789); // no implicit quantization
    CHECK(presets.get_selected_preset().config.opt_string("printfins_options") == saved_before);
    auto second = first;
    set_options(second, {{"gap",0.17}, {"coverage",0.42}});
    presets.load_preset("", "PrintFins B", second);
    CHECK(PF::reset(schema, current, presets.get_selected_preset().config, "gap").at("gap") == 0.17);
    CHECK(PF::serialize(schema, PF::values(schema, presets.get_selected_preset().config),
        presets.get_selected_preset().config) == second.opt_string("printfins_options"));
    REQUIRE(presets.select_preset_by_name("PrintFins A", true));
    CHECK(PF::reset(schema, current, presets.get_selected_preset().config, "gap").at("gap") == 0.31);
    for (const auto &spec : schema["options"]) {
        if (spec.contains("hostSupplied")) continue;
        const auto key = spec.at("key").get<std::string>();
        const auto result = PF::reset(schema, current, presets.get_selected_preset().config, key);
        CHECK(result.at(key) == PF::values(schema, presets.get_selected_preset().config).at(key));
        auto unrelated = result; unrelated.erase(key);
        auto before = changed; before.erase(key);
        CHECK(unrelated == before);
    }
    auto restored = current;
    for (const auto &spec : schema["options"]) {
        if (spec.contains("hostSupplied")) continue;
        const auto reset_value = PF::reset(schema, restored, presets.get_selected_preset().config,
            spec.at("key").get<std::string>());
        restored.set_key_value("printfins_options", new ConfigOptionString(
            PF::serialize(schema, reset_value, presets.get_selected_preset().config)));
    }
    CHECK(restored.opt_string("printfins_options") == saved_before);
    CHECK(restored.option("printfins_options")->serialize() == presets.get_selected_preset().config.option("printfins_options")->serialize());
    set_options(presets.get_edited_preset().config, changed);
    REQUIRE(presets.current_is_dirty());
    presets.get_edited_preset().config.set_key_value("printfins_options",
        new ConfigOptionString(restored.opt_string("printfins_options")));
    CHECK_FALSE(presets.current_is_dirty());
}

TEST_CASE("PrintFins native settings reject corrupt stored values", "[PrintFins][Settings]")
{
    const auto schema = native_schema();
    auto config = DynamicPrintConfig::full_print_config();
    for (const auto &bad : std::vector<PF::Json>{
        {{"gap",0.04}}, {{"gap",1.}}, {{"gap","0.2"}}, {{"sway.on","true"}},
        {{"cutout","custom"}}, {{"unknown",1}}, PF::Json::array()}) {
        set_options(config, bad);
        CHECK_THROWS(PF::values(schema, config));
    }
}

TEST_CASE("PrintFins native Bambu 3MF preserves global and object settings", "[PrintFins][3mf]")
{
    struct TemporaryDirectory {
        std::string previous = temporary_dir();
        TemporaryDirectory() { set_temporary_dir(boost::filesystem::current_path().string()); }
        ~TemporaryDirectory() { set_temporary_dir(previous); }
    } temporary_directory;
    // Unlike copying raw static defaults, the dynamic factory installs the
    // enum-vector dictionaries required by Bambu's JSON project serializer.
    DynamicPrintConfig config;
    for (const auto &key : DynamicPrintConfig::full_print_config().keys()) {
        auto *option = config.option(key, true);
        REQUIRE(option != nullptr);
        if (option->type() == coEnums && !option->nullable())
            REQUIRE(static_cast<ConfigOptionEnumsGeneric *>(option)->keys_map != nullptr);
    }
    config.set_deserialize_strict("support_type", "printfins");
    config.set_key_value("enable_support", new ConfigOptionBool(true));
    set_options(config, {{"threshold",51}, {"tines",true}, {"tineDensity",0.37}, {"gap",0.23},
        {"padStyle","light"}, {"sway.on",true}, {"sway.gripFrom",31}, {"sway.tineSpacing",6.5},
        {"sway.reach",0.22}, {"cutout","arch"}, {"coverage",0.77}, {"plateOnly",true}});
    Model model;
    auto *object = model.add_object("PrintFins settings fixture", "", make_cube(20,20,20));
    object->add_instance();
    object->config.set_key_value("printfins_options", new ConfigOptionString(R"({"gap":0.27,"tines":false,"tineDensity":0.37})"));
    object->volumes.front()->config.set_key_value("printfins_options", new ConfigOptionString(R"({"gap":0.19,"cutout":"arch"})"));
    const auto path = (boost::filesystem::current_path() / boost::filesystem::unique_path("printfins-settings-%%%%-%%%%.3mf")).string();
    INFO(path);
    REQUIRE_FALSE(boost::filesystem::exists(path));
    REQUIRE_FALSE(boost::filesystem::exists(path + ".tmp"));
    StoreParams params;
    params.path = path.c_str(); params.model = &model; params.config = &config;
    params.strategy = SaveStrategy::Zip64 | SaveStrategy::Silence;
    REQUIRE(store_bbs_3mf(params));
    Model reopened;
    DynamicPrintConfig restored;
    ConfigSubstitutionContext substitutions{ForwardCompatibilitySubstitutionRule::Disable};
    PlateDataPtrs plates;
    std::vector<Preset *> project_presets;
    bool native = false;
    Semver version;
    const bool loaded = load_bbs_3mf(path.c_str(), &restored, &substitutions, &reopened,
        &plates, &project_presets, &native, &version, nullptr,
        LoadStrategy::LoadModel | LoadStrategy::LoadConfig | LoadStrategy::Silence);
    release_PlateData_list(plates);
    for (auto *preset : project_presets) delete preset;
    REQUIRE(loaded);
    CHECK(native);
    REQUIRE(reopened.objects.size() == 1);
    REQUIRE(restored.has("support_type"));
    REQUIRE(restored.has("enable_support"));
    REQUIRE(restored.has("printfins_options"));
    REQUIRE(reopened.objects.front()->config.has("printfins_options"));
    REQUIRE(reopened.objects.front()->volumes.size() == 1);
    REQUIRE(reopened.objects.front()->volumes.front()->config.has("printfins_options"));
    CHECK(restored.opt_enum<SupportType>("support_type") == stPrintFins);
    CHECK(restored.opt_bool("enable_support"));
    CHECK(restored.opt_string("printfins_options") == config.opt_string("printfins_options"));
    CHECK(reopened.objects.front()->config.get().opt_string("printfins_options") == object->config.get().opt_string("printfins_options"));
    CHECK(reopened.objects.front()->volumes.front()->config.get().opt_string("printfins_options") == object->volumes.front()->config.get().opt_string("printfins_options"));
    CHECK(reopened.mesh().facets_count() == model.mesh().facets_count());
}

namespace {
class TestOptionsGroup : public OptionsGroup {
public:
    TestOptionsGroup() : OptionsGroup(nullptr, "", "") {}
    const std::vector<ConfigOptionMode> &modes() const { return m_options_mode; }
};

class TestConfigOptionsGroup : public ConfigOptionsGroup {
public:
    explicit TestConfigOptionsGroup(DynamicPrintConfig &config) : ConfigOptionsGroup(nullptr, "", &config) {}
    bool registered(const std::string &key) const { return m_options.count(key) != 0; }
};

Slic3r::GUI::Line option_line(const char *key, ConfigOptionMode mode)
{
    ConfigOptionDef definition;
    definition.opt_key = key;
    definition.mode = mode;
    Slic3r::GUI::Line line{"", ""};
    line.append_option(Option(definition, key));
    return line;
}

TEST_CASE("Bound PrintFins widgets register config metadata before reloading", "[PrintFins][OptionsGroup]")
{
    auto config = DynamicPrintConfig::full_print_config();
    TestConfigOptionsGroup group(config);
    Slic3r::GUI::Line widget{"", ""};
    widget.full_width = 1;
    widget.widget = [](wxWindow *) -> wxSizer * { return nullptr; };
    widget.append_option(group.get_option("printfins_options"));
    group.append_line(widget);
    REQUIRE(group.opt_map().count("printfins_options") == 1);
    CHECK(group.registered("printfins_options"));
    REQUIRE_NOTHROW(group.reload_config());
}
}

TEST_CASE("Object option filtering handles full-width PrintFins widgets", "[PrintFins][OptionsGroup]")
{
    TestOptionsGroup group;
    group.append_line(option_line("support_type", comSimple));
    Slic3r::GUI::Line widget{"", ""};
    widget.full_width = 1;
    widget.widget = [](wxWindow *) -> wxSizer * { return nullptr; };
    SECTION("Unbound widget is removed without indexing the shorter mode vector") {
        group.append_line(widget);
        group.append_line(option_line("excluded", comAdvanced));
        group.remove_option_if([](const std::string &key) { return key != "support_type"; });
        REQUIRE(group.get_lines().size() == 1);
        REQUIRE(group.modes() == std::vector<ConfigOptionMode>{comSimple});
    }
    SECTION("Bound widget survives only in scopes containing its option") {
        widget.append_option(option_line("printfins_options", comSimple).get_options().front());
        group.append_line(widget);
        group.append_line(option_line("excluded", comAdvanced));
        group.append_line(option_line("raft_layers", comAdvanced));
        group.remove_option_if([](const std::string &key) { return key == "excluded"; });
        REQUIRE(group.get_lines().size() == 3);
        REQUIRE(group.get_lines()[1].get_options().front().opt_id == "printfins_options");
        REQUIRE(group.modes() == std::vector<ConfigOptionMode>{comSimple, comAdvanced});
        group.remove_option_if([](const std::string &key) { return key == "printfins_options"; });
        REQUIRE(group.get_lines().size() == 2);
        REQUIRE(group.modes() == std::vector<ConfigOptionMode>{comSimple, comAdvanced});
    }
}
