# Desktop launchers

Launcher ini menjalankan server lokal DictFlow melalui double-click dan membuka
browser default ke `http://127.0.0.1:8000`.

## Windows

Double-click [`windows/DictFlow.bat`](windows/DictFlow.bat). Jika virtual
environment `.venv` tersedia, launcher menggunakannya; jika tidak, launcher
mencari `py` atau `python` di PATH.

## macOS

Double-click [`mac/DictFlow.command`](mac/DictFlow.command). Jika macOS
menolak eksekusi pertama kali, klik kanan file tersebut lalu pilih **Open**.
Launcher akan menggunakan `.venv/bin/python` jika tersedia, atau `python3` dari
PATH.

Tekan `Ctrl+C` pada jendela terminal untuk menghentikan server.

## Mengganti icon

Asset icon disimpan di [`../assets/icons/`](../assets/icons/). Versi Windows
menggunakan `.ico`, sedangkan versi macOS menggunakan PNG resolusi tinggi.
Launcher script tetap sama ketika asset icon diganti.

Untuk tampilan icon pada shortcut desktop, buat shortcut ke launcher lalu pilih
file icon yang sesuai dari folder asset tersebut. Untuk macOS, gunakan
`assets/icons/mac/dictflow-1024x1024.png`.
