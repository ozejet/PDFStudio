# PDF Studio 0.1.019 — local macOS review build

> Documentation record only: this fork does not contain the macOS source changes, DMG, or app ZIP. No public release has been published.

## English

This is a personal, local-review build for Apple Silicon. It is not a public release.

Changes from the checked-out upstream source:

- Added `~/Library/Application Support/PDFStudio` storage on macOS.
- Added a native macOS Save As flow and Safari-specific URL opening.
- Added an AppKit launcher that owns the bundled backend, reuses a running session, and stops the backend on Quit.
- Bundled Python, Python libraries, web assets, fonts, OCR models, license inventories, and exact shipped-asset hashes.
- Added ad-hoc signing, ZIP/DMG packaging, macOS tests, and bilingual operation documentation.
- Corrected the packaged OCR manifest so its hashes describe the actual compressed files shipped in the app.

Verified locally: arm64 binaries; strict deep signature verification for the outer app and nested Save helper; launch from mounted DMG and a copied path containing spaces; repeat launch without a duplicate backend; visible native Save As panel using a synthetic filename; clean quit; loopback-only HTTP; packaged-runtime independence from `.venv` and `/opt/homebrew`; Python tests; UI interaction tests; frontend build; and synthetic PDF/source/OCR/export smoke tests. The final Save button was not clicked by automation after the UI-control request timed out, so destination-file creation through that panel remains a manual review item.

Not verified or not included: Intel Macs, macOS before 13, notarization, public redistribution, Office conversion/LibreOffice, hardware beyond this M2 Pro Mac, personal documents, cloud services, or every kind of complex/interactive/signed PDF.

## ภาษาไทย

นี่คือ build สำหรับตรวจสอบและใช้งานส่วนตัวในเครื่องบน Apple Silicon ไม่ใช่ public release

สิ่งที่เพิ่มจาก source ต้นทางที่ checkout:

- ใช้ `~/Library/Application Support/PDFStudio` สำหรับข้อมูลแอปบน macOS
- เพิ่ม Save As แบบ native ของ macOS และเปิด URL ด้วย Safari
- เพิ่ม AppKit launcher สำหรับควบคุม backend ที่ bundle มา ใช้ session เดิมเมื่อเปิดซ้ำ และหยุด backend เมื่อ Quit
- bundle Python, libraries, web assets, ฟอนต์, OCR models, รายการ license และ hash ของ asset ที่ส่งจริง
- เพิ่มการเซ็นแบบ ad-hoc, การสร้าง ZIP/DMG, test สำหรับ macOS และคู่มือไทย/อังกฤษ
- แก้ manifest ของ OCR ในแพ็กเกจให้ hash ตรงกับไฟล์บีบอัดที่อยู่ในแอปจริง

ตรวจจริงในเครื่องแล้ว: binary แบบ arm64; ตรวจลายเซ็น deep/strict ทั้งแอปหลักและ Save helper; เปิดจาก DMG และจาก path ที่มีช่องว่าง; เปิดซ้ำโดยไม่สร้าง backend ซ้ำ; แสดงหน้าต่าง Save As แบบ native ด้วยชื่อไฟล์สังเคราะห์; Quit แบบสะอาด; HTTP เฉพาะ loopback; runtime ไม่พึ่ง `.venv` หรือ `/opt/homebrew`; Python tests; UI interaction tests; frontend build; และ smoke tests สำหรับ PDF/source/OCR/export ด้วยข้อมูลสังเคราะห์ หลังคำขอควบคุม UI หมดเวลา ระบบอัตโนมัติไม่ได้กดปุ่ม Save ขั้นสุดท้าย ดังนั้นการสร้างไฟล์ปลายทางผ่านหน้าต่างนี้ยังเป็นรายการที่ต้องตรวจด้วยมือ

สิ่งที่ยังไม่ได้ตรวจหรือไม่ได้รวม: Intel Mac, macOS ก่อน 13, notarization, การแจกจ่ายสาธารณะ, Office conversion/LibreOffice, เครื่องอื่นนอกจาก M2 Pro เครื่องนี้, เอกสารส่วนตัว, cloud service และ PDF ซับซ้อน/interactive/ลงลายเซ็นทุกชนิด

## Licensing note / หมายเหตุด้านสิทธิ์

The upstream repository has no project-level license file, so redistribution permission is unresolved. GitHub's public-repository terms permit viewing/forking on the platform but are not a general redistribution license. PyMuPDF is AGPL/commercial; a public build would need the applicable AGPL source/copyleft/notices compliance or a suitable commercial license, plus resolved rights for PDFStudio itself.

repo ต้นทางไม่มี license ระดับโปรเจกต์ จึงยังไม่ชัดเจนว่าสามารถแจกจ่ายต่อได้หรือไม่ เงื่อนไขของ GitHub สำหรับ public repo อนุญาตให้ดู/fork บนแพลตฟอร์ม แต่ไม่ใช่ license แจกจ่ายทั่วไป ส่วน PyMuPDF ใช้ AGPL/commercial; public build ต้องทำตามข้อกำหนด source/copyleft/notices ของ AGPL หรือมี commercial license ที่เหมาะสม และต้องแก้เรื่องสิทธิ์ของ PDFStudio เองด้วย
