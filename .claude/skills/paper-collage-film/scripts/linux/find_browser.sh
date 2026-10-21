# source: выставляет HFT_BROWSER на Linux (Playwright Chromium или системный)
if [ -z "$HFT_BROWSER" ]; then for b in /opt/pw-browsers/chromium-*/chrome-linux/chrome /usr/bin/chromium /usr/bin/chromium-browser /usr/bin/google-chrome; do [ -x "$b" ] && { export HFT_BROWSER="$b"; break; }; done; fi
