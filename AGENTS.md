# RTC Catalog

Reusable RT-Components are listed in:

rtc_catalog/index.json

Before implementing a new component, always search this catalog.

When a suitable RTC exists:

1. Prefer using the existing RTC.
2. Read its detailed metadata.
3. Check its ports, services, and configuration parameters.
4. Do not generate a duplicate RTC unless the existing RTC cannot satisfy the requirements.

Use:

python tools/rtc_search.py "<required functionality>"

to search available RTCs.