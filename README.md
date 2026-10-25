# PDF Studio for Apple Silicon macOS / PDF Studio สำหรับ macOS

> **Documentation preview only / เอกสารสำหรับตรวจสอบเท่านั้น**  
> This public fork currently contains the unchanged upstream source plus newly authored macOS documentation and synthetic-data screenshots. It does **not** contain the adapted macOS application source, DMG, or app ZIP, and there is no public download or release yet.  
> fork สาธารณะนี้มี source ต้นฉบับที่ยังไม่แก้ พร้อมเอกสาร macOS และภาพหน้าจอจากข้อมูลสังเคราะห์เท่านั้น ยังไม่มี source ที่ดัดแปลง, DMG, app ZIP หรือ public release ให้ดาวน์โหลด

Upstream project / โปรเจกต์ต้นฉบับ: [BerlinoPotato/PDFStudio](https://github.com/BerlinoPotato/PDFStudio)  
Original upstream README / README ต้นฉบับ: [view upstream](https://github.com/BerlinoPotato/PDFStudio/blob/main/README.md)

## ภาษาไทย

นี่คือหน้าตรวจสอบงานดัดแปลง PDF Studio สำหรับ **Apple Silicon (arm64), macOS 13 ขึ้นไป** ซึ่งทดสอบในเครื่อง Apple M2 Pro

- แบบแอปที่เตรียมไว้ในเครื่องเป็น `.app` แบบ self-contained: ไม่ต้องใช้ Homebrew หรือเปิด Terminal และเมื่อเปิดแอป หน้าจอจะเปิดใน **Safari**
- engine ทำงานในเครื่องและ bind เฉพาะ `127.0.0.1`; เอกสารทดสอบไม่ได้ถูกอัปโหลดไปยังบริการภายนอก
- แบบ source/Safari ต่างจากแบบ bundled app: แบบ source ต้องมี Python 3.12, Node/npm, `.venv` และ `web/dist`; แบบ bundled app รวม runtime ที่จำเป็นไว้
- build ที่ตรวจสอบเซ็นแบบ ad-hoc และ **ไม่ได้ notarize โดย Apple** ห้ามปิด Gatekeeper หรือลบ quarantine เพื่อบังคับเปิด
- ไม่ได้รวม LibreOffice จึงยังไม่รองรับ Office-to-PDF ใน build นี้
- ทดสอบจนแสดง Save panel ของ macOS ด้วยชื่อไฟล์สังเคราะห์แล้ว แต่ระบบอัตโนมัติ **ยังไม่ได้กด Save ขั้นสุดท้าย** จึงยังไม่ยืนยันการสร้างไฟล์ปลายทางผ่าน panel นั้น

อ่าน [คู่มือภาษาไทย](docs/macos/README.th.md) และ [บันทึกการตรวจสอบ 0.1.019](docs/macos/RELEASE_NOTES-0.1.019.md)

## English

This page records a locally tested adaptation of PDF Studio for **Apple Silicon (arm64), macOS 13 or later**, verified on an Apple M2 Pro Mac.

- The locally prepared `.app` is self-contained: it does not require Homebrew or Terminal, and launching it opens the interface in **Safari**.
- Its engine runs on the Mac and binds only to `127.0.0.1`; synthetic test documents were not uploaded to an external service.
- The source/Safari variant is distinct from the bundled app: source mode needs Python 3.12, Node/npm, `.venv`, and `web/dist`; the bundled app carries its required runtime.
- The reviewed build is ad-hoc signed and **not Apple-notarized**. Do not disable Gatekeeper or remove quarantine to force it to run.
- LibreOffice is not bundled, so Office-to-PDF conversion is unavailable in this build.
- Automation reached the native macOS Save panel with a synthetic filename, but **did not click the final Save button**; destination-file creation through that panel remains unverified.

Read the [English guide](docs/macos/README.en.md) and [0.1.019 review notes](docs/macos/RELEASE_NOTES-0.1.019.md).

## Screenshots / ภาพหน้าจอ

All screenshots are genuine captures of the final local review build and use synthetic files only.

### DMG installation / การติดตั้งจาก DMG

![DMG installation window](docs/screenshots/macos/01-dmg-install.png)

### Safari workflow / การใช้งานใน Safari

![Synthetic PDF open in Safari](docs/screenshots/macos/02-safari-read.png)

### Native Save panel / หน้าต่าง Save ของ macOS

![Native Save panel with synthetic filename](docs/screenshots/macos/03-native-save-as.png)

## Publication and licensing status / สถานะการเผยแพร่และสิทธิ์

Only this documentation and the synthetic screenshots are published in the fork. The adapted source and binaries remain unpublished pending clarification of redistribution rights.

The upstream repository has no project-level license file. GitHub permits viewing and forking public repositories on its platform, but that is not a general redistribution license. PyMuPDF is AGPL/commercial and requires separate compliance. This fork does not assign a license to upstream code or claim legal clearance.

มีการเผยแพร่เฉพาะเอกสารและภาพจากข้อมูลสังเคราะห์ใน fork นี้ ส่วน source ที่แก้และ binary ยังไม่เผยแพร่จนกว่าจะชัดเจนเรื่องสิทธิ์แจกจ่าย โปรเจกต์ต้นทางไม่มี license ระดับโปรเจกต์ และ PyMuPDF มีเงื่อนไข AGPL/commercial แยกต่างหาก fork นี้ไม่ได้กำหนด license ให้โค้ดต้นทางและไม่ได้อ้างว่าได้รับสิทธิ์เผยแพร่แล้ว
