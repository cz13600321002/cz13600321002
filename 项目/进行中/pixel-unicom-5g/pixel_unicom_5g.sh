#!/usr/bin/env bash
# Pixel 9 Pro XL + 中国联通 5G：诊断 / 有限写入。
# 默认只读。--apply 才改联通侧网络偏好，不碰 Tello 账号/钱包/v2ray。
set -euo pipefail

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
fi

need_adb() {
  if ! command -v adb >/dev/null 2>&1; then
    echo "本机没有 adb。先装 Android platform-tools，再把 Pixel USB 调试打开。" >&2
    exit 1
  fi
  if ! adb get-state >/dev/null 2>&1; then
    echo "adb 看不到设备。插 USB、解锁、点允许调试后再跑。" >&2
    adb devices -l >&2 || true
    exit 1
  fi
}

is_unicom() {
  local mcc="${1:-}" mnc="${2:-}"
  [[ "$mcc" == "460" && ( "$mnc" == "01" || "$mnc" == "06" || "$mnc" == "09" ) ]]
}

is_us_tmobile_family() {
  local mcc="${1:-}"
  [[ "$mcc" == "310" || "$mcc" == "311" || "$mcc" == "312" ]]
}

dump_state() {
  echo "======== 设备 ========"
  adb shell getprop ro.product.model
  adb shell getprop ro.build.version.release
  adb shell getprop ro.build.id
  echo
  echo "======== SIM / 订阅 ========"
  adb shell dumpsys isub | awk '
    /mSubscriptionInfoList|SubscriptionInfo|mId=|mIccId=|mNumber=|mMcc=|mMnc=|mDisplayName=|mCarrierName=|mSimSlotIndex=/ {
      print
    }' | head -n 80
  echo
  echo "======== 数据默认订阅 ========"
  adb shell settings get global multi_sim_data_call || true
  adb shell dumpsys isub | awk '/default data|DefaultDataSubId|mDefaultDataSubId/ {print; found=1} END{if(!found) print "(未直接读到 DefaultDataSubId)"}'
  echo
  echo "======== 联通/各卡驻网 ========"
  adb shell dumpsys telephony.registry | awk '
    /mPhoneId=|mSubId=|mServiceState|mDataNetworkType|mVoiceNetworkType|nrState|mIsNrAvailable|isNrAvailable|isEnDcAvailable|mOperatorAlpha|mDataOperator|LTE_BAND|NR_BAND|mRilDataRadioTechnology/ {
      print
    }' | head -n 120
  echo
  echo "======== gsm.network.type / 运营商 ========"
  adb shell getprop gsm.operator.numeric
  adb shell getprop gsm.operator.alpha
  adb shell getprop gsm.network.type
  adb shell getprop gsm.sim.operator.numeric
  echo
  echo "======== APN 线索 ========"
  adb shell dumpsys telephony.apn | head -n 80 || true
  adb shell content query --uri content://telephony/carriers/preferapn 2>/dev/null | head -n 40 || true
}

pick_unicom_sub() {
  # 尽力从 isub 抠出联通 subId。失败则留空，--apply 会中止。
  adb shell dumpsys isub | awk '
    BEGIN { id=""; mcc=""; mnc=""; }
    /mId=|id=/ {
      if (match($0, /mId=([0-9]+)/, a)) id=a[1]
      else if (match($0, /id=([0-9]+)/, a) && id=="") id=a[1]
    }
    /mMcc=/ { if (match($0, /mMcc=([0-9]+)/, a)) mcc=a[1] }
    /mMnc=/ { if (match($0, /mMnc=([0-9]+)/, a)) mnc=a[1] }
    {
      if (id != "" && mcc == "460" && (mnc == "01" || mnc == "06" || mnc == "09")) {
        print id
        exit
      }
    }
  ' | head -n 1
}

apply_unicom() {
  local sub
  sub="$(pick_unicom_sub || true)"
  if [[ -z "${sub}" ]]; then
    echo "没有自动识别到联通订阅（46001/06/09）。先看上面的 dumpsys，把联通 subId 手工确认后再跑。" >&2
    echo "不会改 Tello，也不会写任何覆盖。" >&2
    exit 2
  fi
  echo "联通 subId=${sub}。写入仅针对这张卡。"
  # 默认数据 → 联通（不关 Tello 卡本身，只改默认数据）
  adb shell settings put global multi_sim_data_call "${sub}" || true
  # NR/LTE 偏好。26=NR_LTE_GSM_WCDMA，27=NR_LTE_TDSCDMA_CDMA_EVDO_GSM_WCDMA
  adb shell settings put global preferred_network_mode "${sub},26" || true
  adb shell settings put global "preferred_network_mode${sub}" 26 || true
  # 尝试 Carrier Config（无 Shizuku/特权时可能失败，失败不中止）
  adb shell cmd carrier_config 2>/dev/null | head -n 20 || true
  adb shell cmd carrier_config override 0 carrier_nr_availabilities_int_array i=1,i=2 2>/dev/null || true
  adb shell cmd carrier_config override 0 carrier_volte_available_bool true 2>/dev/null || true
  adb shell cmd carrier_config override 0 carrier_vonr_available_bool true 2>/dev/null || true
  adb shell cmd carrier_config override 0 vonr_enabled_bool true 2>/dev/null || true
  adb shell cmd carrier_config override 0 vonr_setting_visibility_bool true 2>/dev/null || true
  echo "飞行模式一轮…"
  adb shell cmd connectivity airplane-mode enable || adb shell settings put global airplane_mode_on 1
  sleep 8
  adb shell cmd connectivity airplane-mode disable || adb shell settings put global airplane_mode_on 0
  adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false >/dev/null 2>&1 || true
  echo "等 20 秒重新驻网…"
  sleep 20
  echo
  echo "======== 写入后再读 ========"
  adb shell getprop gsm.network.type
  adb shell dumpsys telephony.registry | awk '
    /mDataNetworkType|nrState|isNrAvailable|isEnDcAvailable|mDataOperator/ {print}
  ' | head -n 40
  echo
  echo "若仍是 LTE 且 isNrAvailable=false：先确认联通 App 已开通 5G，再用 TurboIMS/Pixel IMS 专家项写 1,2，APN 试 wonet。"
}

need_adb
dump_state
if [[ "$APPLY" -eq 1 ]]; then
  echo
  echo "======== --apply 联通侧 ========"
  apply_unicom
else
  echo
  echo "只读结束。确认联通 sub 无误后执行："
  echo "  bash 项目/进行中/pixel-unicom-5g/pixel_unicom_5g.sh --apply"
fi
