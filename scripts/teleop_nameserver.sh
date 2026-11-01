# Shared localhost:2809 NameService. Source after processes.sh; no RTC lifecycle here.
nameserver_list() {
  timeout 7 "$PY" "$ROOT/scripts/nameserver_probe.py" "$RTCSERVER"
}
scoped_rtcat() {
  timeout 7 "$PY" "$ROOT/scripts/rtcat_scoped.py" "$1" "/$RTCSERVER/gui-joystick-1.rtc" "/$RTCSERVER/teleop-controller-1.rtc"
}
prepare_nameserver() {
  begin_run
  local endpoint_ip
  endpoint_ip=$("$PY" -c 'import sys; sys.path.insert(0,sys.argv[1]); from configure_wsl_rtc_endpoint import resolve_address; print(resolve_address())' "$ROOT/scripts") || return 1
  # This is the verified system service in this WSL deployment. The root helper
  # records the first application per endpoint configuration and never restarts
  # a healthy service again on routine RTC startup.
  if systemctl show omniorb-nameserver.service -p ExecStart --value 2>/dev/null | grep -Fq '/usr/bin/omniNames'; then
    if [[ $(id -u) == 0 ]]; then
      /usr/bin/python3 "$ROOT/scripts/apply_nameserver_endpoint.py" "$endpoint_ip" || return 1
    else
      /mnt/c/Windows/System32/wsl.exe -d Ubuntu -u root --exec /usr/bin/python3 "$ROOT/scripts/apply_nameserver_endpoint.py" "$endpoint_ip" || return 1
    fi
    nameserver_list > "$RUN_DIR/nameserver-health.txt" 2>&1 || return 1
    return 0
  fi
  local attempt
  for attempt in 1 2; do
    if nameserver_list > "$RUN_DIR/nameserver-health.txt" 2>&1; then
      echo "REUSE HEALTHY NAMESERVER $RTCSERVER"
      return 0
    fi
  done
  # Recover a known system service with its original service configuration.
  local pid exe
  pid=$(systemctl show omniorb-nameserver.service -p MainPID --value 2>/dev/null) || pid=0
  if [[ $pid =~ ^[0-9]+$ && $pid != 0 ]]; then
    exe=$(readlink -f "/proc/$pid/exe" 2>/dev/null) || exe=''
    # Root-owned /proc can be hidden; service ExecStart provides identity too.
    if [[ $exe == /usr/bin/omniNames ]] || systemctl show omniorb-nameserver.service -p ExecStart --value | grep -Fq '/usr/bin/omniNames'; then
      echo 'RECOVER unhealthy omniorb-nameserver.service on port 2809'
      if [[ $(id -u) == 0 ]]; then
        systemctl restart omniorb-nameserver.service || return 1
      else
        /mnt/c/Windows/System32/wsl.exe -d Ubuntu -u root --exec systemctl restart omniorb-nameserver.service || return 1
      fi
    else
      echo 'Unrecognized NameService service identity; refusing restart' >&2; return 1
    fi
  elif owned_alive nameserver; then
    echo 'RECOVER unhealthy owned NameService'
    stop_owned nameserver || return 1
    start_owned nameserver /usr/bin/omniNames -start 2809 -always -datadir "$RUNTIME/naming" -errlog "$RUN_DIR/nameserver-native.log" || return 1
  else
    local status=$?; [[ $status != 2 ]] || return 2
    if ss -lnt | grep -q ':2809 '; then
      echo 'Port 2809 has an unidentified/unresponsive listener; refusing to kill it' >&2; return 1
    fi
    start_owned nameserver /usr/bin/omniNames -start 2809 -always -datadir "$RUNTIME/naming" -errlog "$RUN_DIR/nameserver-native.log" || return 1
  fi
  for attempt in $(seq 1 20); do
    if nameserver_list > "$RUN_DIR/nameserver-health-after-recovery.txt" 2>&1; then
      echo "NAMESERVER READY $RTCSERVER"; return 0
    fi
    sleep .3
  done
  cat "$RUN_DIR/nameserver-health-after-recovery.txt" >&2
  return 1
}
