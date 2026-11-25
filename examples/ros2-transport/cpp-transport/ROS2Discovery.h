// -*- C++ -*-
/*!
 * @file  ROS2Discovery.h
 * @brief Named ROS 2 node discovery API
 */

#pragma once

namespace RTC { class Manager; }

namespace openrtm_ros2 {
/*!
 * @if jp
 * @brief 設定された ROS 2 ノードの通知を開始する
 * @param manager ノード名と名前空間を取得する RTC Manager
 * @else
 * @brief Start announcing the configured ROS 2 node
 * @param manager RTC Manager supplying the node name and namespace
 * @endif
 */
void start_discovery(RTC::Manager& manager);
}
