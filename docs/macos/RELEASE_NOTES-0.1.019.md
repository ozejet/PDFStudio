# PDF Studio 0.1.019 — experimental Apple Silicon macOS pre-release

## English

This is an experimental public pre-release for Apple Silicon. It is ad-hoc signed,
not Apple notarized, and is not represented as production-ready.

Changes from the checked-out upstream source:

- Added `~/Library/Application Support/PDFStudio` storage on macOS.
- Added a native macOS Save As flow and Safari-specific URL opening.
- Added an AppKit launcher that owns the bundled backend, reuses a running session, and stops the backend on Quit.
- Bundled Python, Python libraries, web assets, fonts, OCR models, license inventories, and exact shipped-asset hashes.
- Added ad-hoc signing, ZIP/DMG packaging, macOS tests, and bilingual operation documentation.
- Corrected the packaged OCR manifest so its hashes describe the actual compressed files shipped in the app.

Verified locally: arm64 binaries; strict deep signature verification for the outer app and nested Save helper; launch from mounted DMG and a copied path containing spaces; repeat launch without a duplicate backend; visible native Save As panel using a synthetic filename; clean quit; loopback-only HTTP; packaged-runtime independence from `.venv` and `/opt/homebrew`; Python tests; UI interaction tests; frontend build; and synthetic PDF/source/OCR/export smoke tests. The final Save button was not clicked by automation after the UI-control request timed out, so destination-file creation through that panel remains a manual review item.

Not verified or not included: Intel Macs, macOS before 13, notarization, Office conversion/LibreOffice, hardware beyond this M2 Pro Mac, personal documents, cloud services, or every kind of complex/interactive/signed PDF. The final click in the native Save panel remains unverified.

## ภาษาไทย

นี่คือ public pre-release แบบทดลองสำหรับ Apple Silicon เซ็นแบบ ad-hoc ไม่ได้ notarize
โดย Apple และไม่ได้อ้างว่าพร้อมใช้งานระดับ production

สิ่งที่เพิ่มจาก source ต้นทางที่ checkout:

- ใช้ `~/Library/Application Support/PDFStudio` สำหรับข้อมูลแอปบน macOS
- เพิ่ม Save As แบบ native ของ macOS และเปิด URL ด้วย Safari
- เพิ่ม AppKit launcher สำหรับควบคุม backend ที่ bundle มา ใช้ session เดิมเมื่อเปิดซ้ำ และหยุด backend เมื่อ Quit
- bundle Python, libraries, web assets, ฟอนต์, OCR models, รายการ license และ hash ของ asset ที่ส่งจริง
- เพิ่มการเซ็นแบบ ad-hoc, การสร้าง ZIP/DMG, test สำหรับ macOS และคู่มือไทย/อังกฤษ
- แก้ manifest ของ OCR ในแพ็กเกจให้ hash ตรงกับไฟล์บีบอัดที่อยู่ในแอปจริง

ตรวจจริงในเครื่องแล้ว: binary แบบ arm64; ตรวจลายเซ็น deep/strict ทั้งแอปหลักและ Save helper; เปิดจาก DMG และจาก path ที่มีช่องว่าง; เปิดซ้ำโดยไม่สร้าง backend ซ้ำ; แสดงหน้าต่าง Save As แบบ native ด้วยชื่อไฟล์สังเคราะห์; Quit แบบสะอาด; HTTP เฉพาะ loopback; runtime ไม่พึ่ง `.venv` หรือ `/opt/homebrew`; Python tests; UI interaction tests; frontend build; และ smoke tests สำหรับ PDF/source/OCR/export ด้วยข้อมูลสังเคราะห์ หลังคำขอควบคุม UI หมดเวลา ระบบอัตโนมัติไม่ได้กดปุ่ม Save ขั้นสุดท้าย ดังนั้นการสร้างไฟล์ปลายทางผ่านหน้าต่างนี้ยังเป็นรายการที่ต้องตรวจด้วยมือ

สิ่งที่ยังไม่ได้ตรวจหรือไม่ได้รวม: Intel Mac, macOS ก่อน 13, notarization, Office conversion/LibreOffice, เครื่องอื่นนอกจาก M2 Pro เครื่องนี้, เอกสารส่วนตัว, cloud service และ PDF ซับซ้อน/interactive/ลงลายเซ็นทุกชนิด ส่วนการกด Save ขั้นสุดท้ายใน native panel ยังไม่ได้ยืนยัน

## Licensing note / หมายเหตุด้านสิทธิ์

The upstream owner authorized this adaptation's source and macOS packages under GNU AGPLv3 in [Issue #1](https://github.com/BerlinoPotato/PDFStudio/issues/1#issuecomment-6397084771), limited to PDFStudio code for which that owner holds copyright. This does not change the original repository's license or grant third-party rights. PyMuPDF 1.28.0 is used under its GNU AGPLv3 option, with the exact source archive distributed beside the binaries.

เจ้าของ upstream อนุญาตให้เผยแพร่ source และแพ็กเกจ macOS ของงานดัดแปลงนี้ภายใต้ GNU AGPLv3 ใน [Issue #1](https://github.com/BerlinoPotato/PDFStudio/issues/1#issuecomment-6397084771) โดยจำกัดเฉพาะโค้ด PDFStudio ที่เจ้าของถือสิทธิ์ คำอนุญาตนี้ไม่เปลี่ยน license ของ repo ต้นฉบับและไม่ให้สิทธิ์ของ dependency ภายนอก ส่วน PyMuPDF 1.28.0 ใช้ทางเลือก GNU AGPLv3 พร้อมแนบ source archive ที่ตรงรุ่นไว้ข้าง binary

## Prepared artifact checksums / checksum ของไฟล์ที่เตรียมไว้

Release assets are published with matching source and are verified against these hashes.

```text
83d12722d85d35c3e1abaaafcd75afce54d9926bba186b3a76a613c2228d2238  PDFStudio-0.1.019-arm64.app.zip
c7a7dee2959469bd6bb472b606fa71c5c9ac68f4f9f0028bca77767bf7915aa8  PDFStudio-0.1.019-arm64.dmg
e53f3567403a92da15caa9e7ae0164327fff48817e9f40175367fb9de524258d  pymupdf-1.28.0.tar.gz
```
