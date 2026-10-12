# Mock Data

Mock data digunakan sebagai data simulasi untuk kebutuhan pengembangan, pengujian, dan pembuatan prototype (POC/MVP). Data ini tidak merepresentasikan data asli dan hanya digunakan untuk memastikan alur aplikasi, API, dan tampilan UI berjalan dengan baik sebelum terhubung ke backend atau data production.

## Lokasi

Semua mock data disimpan di folder `data/`.

## Files

| File                    | Name           | Description                                              |
| ----------------------- | -------------- | -------------------------------------------------------- |
| data/data-penduduk.json | Data Penduduk  | Data statistik jumlah penduduk per wilayah               |
| data/data-sentimen.json | Data Sentimen  | Data statistik sentimen masyarakat terhadap layanan publik |

## Implementasi

| File     | Path                      | Name                    | Description                                         | Endpoint              | Status   |
| -------- | ------------------------- | ----------------------- | --------------------------------------------------- | --------------------- | -------- |
| Mock API | src/mocks/api/penduduk.ts | Mock Penduduk Handler   | Handler mock untuk data statistik penduduk          | `/api/penduduk`       | 🔄 Planned |
| Mock API | src/mocks/api/sentimen.ts | Mock Sentimen Handler   | Handler mock untuk data statistik sentimen publik   | `/api/sentimen`       | 🔄 Planned |

## Aturan

- Jangan modifikasi file di `data/` langsung — duplikat dulu jika perlu edit
- Data hanya dipakai di stage POC dan MVP
- Lihat [.claude/rules/project-scope.md](../.claude/rules/project-scope.md) untuk konvensi scope POC/MVP
