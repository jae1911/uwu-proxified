from waitress import serve

import uwu

serve(uwu.app, host="0.0.0.0", port=5000)
