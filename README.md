[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/mRmkZGKe)
# Network Programming - Assignment G01

## Anggota Kelompok
| Nama           | NRP        | Kelas     |
| ---            | ---        | ----------|
| Rifat Qurratu Aini Irwandi               | 5025241233           | D          |
| Mayandra Suhaira Frisiandi               | 5025241240           | D          |

## Link Youtube (Unlisted)
Link ditaruh di bawah ini
```

```

## Penjelasan Program

Program ini terdiri dari 5 file python, 1 file client dan 4 file server dengan 4 metode berbeda.

### 1. client.py
  `client.py` bertujuan sebagai end user yang akan berinteraksi dengan semua server. 
  1. Klien menyiapkan alamat HOST (127.0.0.1) dan PORT (9999). Begitu program dijalankan, klien mencoba mengetuk pintu server. Jika server merespons, status menjadi [CONNECTED].
  2. Program masuk ke dalam loop (perulangan) untuk menunggu input dari user. Di sini, fungsi main() bertugas menangkap apa yang kamu ketik.
  3. Setelah user mengetik perintah seperti /list, fungsi `send_command` akan membungkus teks tersebut menjadi paket data (bytes) dan mengirimkannya ke server.
  4. Setelah mengirim perintah, klien akan menjalankan fungsi `receive_response` untuk mendengarkan jawaban dari server. Server membalas dalam format JSON yang berisi status success atau error.
  5. Tipe-tipe response:
     - `/list`: user menerima daftar nama file dan menampilkannya di layar.
     - `/upload`: user mengirim info file (nama & ukuran), menunggu server bilang "Ready", lalu user mengirim isi filenya potongan demi potongan (chunks).
     - `/download`: user meminta file, server memberi tahu ukuran, klien bilang "Ready", lalu server mengirim data filenya ke user untuk disimpan.
     - `/quit` : User mengirim pesan putus ke server, lalu menutup koneksi `(sock.close())` dan program selesai.
       
### 2. server-sync.py
### 3. server-select.py
### 4. server-poll.py
### 5. server-thread.py

## Screenshot Hasil
