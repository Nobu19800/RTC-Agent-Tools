#include "Control.hpp"
#include "Pdu.hpp"
#include <gtest/gtest.h>
#include <limits>

TEST(Control, BoundsDisplacementAndSetsSpeed)
{
  const auto move = drone::move_target(240, 0, {1, 2}, 0.1, true);
  ASSERT_TRUE(move);
  EXPECT_DOUBLE_EQ(move->x, 6);
  EXPECT_DOUBLE_EQ(move->y, 2);
  EXPECT_DOUBLE_EQ(move->z, 1);
  EXPECT_DOUBLE_EQ(move->speed, 6);
  const auto partial = drone::move_target(0, -60, {1, 2}, 0, true);
  ASSERT_TRUE(partial);
  EXPECT_DOUBLE_EQ(partial->y, -0.5);
}

TEST(Control, IgnoresInvalidAndInactiveInput)
{
  EXPECT_FALSE(drone::move_target(0, 0, {0, 0}, 0, true));
  EXPECT_FALSE(drone::move_target(120, 0, {0, 0}, 0.3, true));
  EXPECT_FALSE(drone::move_target(120, 0, {0, 0}, -1, true));
  EXPECT_FALSE(drone::move_target(120, 0, {0, 0}, 0, false));
  const auto nan = std::numeric_limits<double>::quiet_NaN();
  EXPECT_FALSE(drone::move_target(nan, 0, {0, 0}, 0, true));
  EXPECT_FALSE(drone::move_target(120, 0, {nan, 0}, 0, true));
  EXPECT_FALSE(drone::move_target(120, 0, {0, nan}, nan, true));
  EXPECT_FALSE(drone::move_target(120, 0, {0, nan}, 0, true));
}

TEST(Control, ChecksResponseAndTimeout)
{
  using drone::Response;
  EXPECT_EQ(drone::response(false, true, 0, 2), Response::accepted);
  EXPECT_EQ(drone::response(false, true, 1, 2), Response::rejected);
  EXPECT_EQ(drone::response(true, true, 0, 2), Response::waiting);
  EXPECT_EQ(drone::response(false, false, 0, 16), Response::timed_out);
}

TEST(Pdu, RoundTripAndPadding)
{
  auto payload = drone::encode<double, 48>(3.5);
  const auto value = drone::decode<double>(payload);
  ASSERT_TRUE(value);
  EXPECT_DOUBLE_EQ(*value, 3.5);
  EXPECT_EQ(payload.back(), 0);
}

TEST(Pdu, RejectsBadMetadata)
{
  const auto valid = drone::encode<double, 48>(3.5);
  HakoPduMetaDataType header{};
  std::memcpy(&header, valid.data(), sizeof(header));
  const auto rejects = [&valid](HakoPduMetaDataType altered) {
    auto bytes = valid;
    std::memcpy(bytes.data(), &altered, sizeof(altered));
    return !drone::decode<double>(bytes);
  };
  auto bad = header;
  bad.magicno = 0;
  EXPECT_TRUE(rejects(bad));
  bad = header;
  bad.version = 0;
  EXPECT_TRUE(rejects(bad));
  bad = header;
  bad.base_off = 0;
  EXPECT_TRUE(rejects(bad));
  bad = header;
  bad.heap_off = bad.total_size + 1;
  EXPECT_TRUE(rejects(bad));
  bad = header;
  bad.total_size = 49;
  EXPECT_TRUE(rejects(bad));
  bad = header;
  bad.heap_off = bad.base_off - 1;
  EXPECT_TRUE(rejects(bad));
  bad = header;
  bad.heap_off = bad.base_off;
  EXPECT_TRUE(rejects(bad));
}
