#pragma once
#include <pdu_primitive_ctypes.h>
#include <array>
#include <cstring>
#include <optional>

namespace drone {
template<class Value, std::size_t Capacity>
using Payload = std::array<char, Capacity>;

template<class Value, std::size_t Capacity>
Payload<Value, Capacity> encode(const Value& value)
{
  constexpr auto offset = HAKO_PDU_META_DATA_SIZE();
  constexpr auto size = offset + sizeof(Value);
  static_assert(size <= Capacity);
  Payload<Value, Capacity> payload{};
  HakoPduMetaDataType meta{HAKO_PDU_META_DATA_MAGICNO, HAKO_PDU_META_DATA_VERSION,
                          offset, size, size, 0, 0, {0, 0}};
  std::memcpy(payload.data(), &meta, sizeof(meta));
  std::memcpy(payload.data() + offset, &value, sizeof(value));
  return payload;
}

template<class Value, std::size_t Capacity>
std::optional<Value> decode(const std::array<char, Capacity>& payload)
{
  static_assert(Capacity >= sizeof(HakoPduMetaDataType));
  HakoPduMetaDataType meta{};
  std::memcpy(&meta, payload.data(), sizeof(meta));
  if (meta.magicno != HAKO_PDU_META_DATA_MAGICNO ||
      meta.version != HAKO_PDU_META_DATA_VERSION ||
      meta.base_off < HAKO_PDU_META_DATA_SIZE() ||
      meta.heap_off > meta.total_size || meta.total_size > Capacity ||
      meta.heap_off < meta.base_off || meta.heap_off - meta.base_off < sizeof(Value)) {
    return std::nullopt;
  }
  Value value{};
  std::memcpy(&value, payload.data() + meta.base_off, sizeof(value));
  return value;
}
}
