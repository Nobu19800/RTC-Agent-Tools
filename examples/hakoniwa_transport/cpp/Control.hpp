#pragma once
#include <array>
#include <cmath>
#include <optional>

namespace drone {
struct Move {
  double x, y, z, speed;
};

inline std::optional<Move> move_target(double x, double y,
                                       const std::array<double, 2>& position,
                                       double input_age, bool airborne)
{
  if (!airborne || !std::isfinite(input_age) || input_age < 0 || input_age >= 0.3 ||
      !std::isfinite(position[0]) || !std::isfinite(position[1])) {
    return std::nullopt;
  }
  x /= 120.0;
  y /= 120.0;
  const auto magnitude = std::hypot(x, y);
  if (!std::isfinite(magnitude) || magnitude < 0.05) {
    return std::nullopt;
  }
  const double step = magnitude > 1.0 ? 5.0 / magnitude : 5.0;
  return Move{position[0] + step * x, position[1] + step * y, 1.0, 6.0};
}

enum class Response { waiting, accepted, rejected, timed_out };
inline Response response(bool request, bool result, int code, double elapsed)
{
  if (result && !request) {
    return code == 0 ? Response::accepted : Response::rejected;
  }
  return elapsed > 15.0 ? Response::timed_out : Response::waiting;
}
}
