#ifndef slic3r_GUI_PrintFinsSettings_hpp_
#define slic3r_GUI_PrintFinsSettings_hpp_

#include "libslic3r/PrintConfig.hpp"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace Slic3r::GUI::PrintFinsSettings {
using Json = nlohmann::json;

// Host presentation only. Never change the verified upstream schema on disk.
inline Json native_schema(Json schema)
{
    for (auto &spec : schema.at("options")) {
        const auto key = spec.at("key").get<std::string>();
        if (key == "threshold" || key == "sway.gripFrom") spec["step"] = 1.;
        else if (key == "tineDensity" || key == "coverage" || key == "sway.reach" || key == "gap") spec["step"] = 0.01;
        else if (key == "sway.tineSpacing") spec["step"] = 0.5;
        // gap remains 0.10..0.40: both original entry-point validators enforce it.
    }
    return schema;
}

inline void validate(const Json &spec, const Json &value)
{
    const auto type = spec.at("type").get<std::string>();
    bool valid = false;
    if (type == "number" && value.is_number()) {
        const double v = value.get<double>();
        valid = std::isfinite(v) && v >= spec.at("min").get<double>() && v <= spec.at("max").get<double>();
    } else if (type == "bool") valid = value.is_boolean();
    else if (type == "choice")
        for (const auto &choice : spec.at("choices")) valid = valid || choice.at("value") == value;
    if (!valid) throw std::runtime_error("Invalid PrintFins setting: " + spec.at("key").get<std::string>());
}

inline Json values(const Json &schema, const DynamicPrintConfig &config)
{
    const auto *option = config.option<ConfigOptionString>("printfins_options");
    const auto saved = Json::parse(option ? option->value : "{}");
    if (!saved.is_object()) throw std::runtime_error("Invalid PrintFins settings in this project.");
    Json result = Json::object();
    for (const auto &spec : schema.at("options")) {
        if (spec.contains("hostSupplied")) continue;
        const auto key = spec.at("key").get<std::string>();
        const auto value = saved.value(key, spec.at("default"));
        validate(spec, value);
        result[key] = value;
    }
    for (auto it = saved.begin(); it != saved.end(); ++it)
        if (!result.contains(it.key())) throw std::runtime_error("Unknown PrintFins setting: " + it.key());
    return result;
}

inline double step(const Json &spec, double value, int direction)
{
    validate(spec, value);
    // An increment, not quantization: retain valid typed and saved decimal values.
    const double next = std::clamp(value + direction * spec.at("step").get<double>(),
        spec.at("min").get<double>(), spec.at("max").get<double>());
    return std::round(next * 1e12) / 1e12;
}

inline Json reset(const Json &schema, const DynamicPrintConfig &current,
                  const DynamicPrintConfig &preset, const std::string &key)
{
    auto result = values(schema, current);
    result.at(key) = values(schema, preset).at(key);
    return result;
}

inline std::string serialize(const Json &schema, const Json &current, const DynamicPrintConfig &preset)
{
    // Bambu compares the aggregate config string for preset dirtiness. Once all
    // values match, restore its exact saved representation, including sparse JSON.
    if (current == values(schema, preset)) {
        const auto *option = preset.option<ConfigOptionString>("printfins_options");
        return option ? option->value : "{}";
    }
    return current.dump();
}
}
#endif
