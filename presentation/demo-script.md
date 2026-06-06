# LeaseLens Demo Script (about 3.5 minutes)

One screen recording with voiceover. Speak over a few slides, switch to the live
app for the demo, then finish on the closing slides. Keep the delivery calm and
clear.

Before recording: run `cd leaselens && ./run.sh`, open `http://localhost:8080`,
and restart the server so nothing is pre-reviewed. Open the deck in another
window. Hide notifications and the bookmarks bar.

`[SLIDE]` marks what is on screen. `[DO]` marks what you click. Everything else
is what you say.

---

### 0:00  Open (Slide 1)

`[SLIDE 1: title]`

"I'm Sai. This is LeaseLens. It reads incoming leases automatically and flags
only the ones that need a person to review them. I'll show you what it does, why
it is useful, and how I built it."

### 0:20  Why it is useful (Slide 2)

`[SLIDE 2: why it's useful]`

"Property managers receive signed leases as PDFs. Today, someone opens each one
and types the rent, the deposit, and the dates into their system by hand. It is
slow, and the errors that cost the most, like a deposit above the legal limit,
are the easiest to miss at volume. LeaseLens is built for leasing teams that
process leases in bulk. Clean leases pass through automatically, and people only
review the exceptions."

### 0:45  How it works (Slide 3)

`[SLIDE 3: six steps]`

"Every lease goes through the same six steps. It confirms the document is a
lease, runs a gate check that includes OCR for scans, extracts the key terms,
validates them against rules, reviews the contract text, and then hands the
result to a person. The first five steps are automatic. Now I'll open the app."

### 1:05  Live demo (switch to the app)

`[DO]` Switch to the browser and show the inbox.

"This is the inbox. Eleven leases have come in. Green means clean, orange and red
have issues, and two were rejected. Every row was processed automatically."

`[DO]` Click the `lease_illegal_deposit` row.

"When I open a lease, the extracted fields appear on the right: tenant, rent,
deposit, and dates. It flagged the problem clearly. The security deposit is
13,000 dollars, more than twice the monthly rent, which is above the legal cap in
most states. I did not write a rule for this specific lease. It checks every
lease against that policy."

`[DO]` Add a short note and click Override or Confirm.

"I can confirm or override the result, and the decision is recorded."

`[DO]` Open `lease_risky_clause`.

"This lease has valid numbers, but the system read the contract text and flagged
a non-standard clause where the tenant waives the return of their deposit."

`[DO]` Open `lease_scanned_ocr` and point to the OCR tag.

"This document was a scan with no readable text inside it. The system ran OCR,
read it, and extracted the same fields as a normal PDF."

`[DO]` Optional: upload a fresh lease or load a sample.

"It also works in real time. I can upload a new lease and it is processed in
under a second."

### 2:30  How it is built (Slide 5)

`[SLIDE 5: how it's built]`

"A note on the build. The backend is Python and FastAPI. It uses pdfplumber to
read text and Tesseract for OCR on scans. The main design choice is that reading
a document has two interchangeable modes behind one interface. One is a fast
offline mode that needs no API key. The other uses an AI model and turns on by
adding a key, with no other changes to the app. The validation rules are simple
and readable, and a test suite covers the sample leases."

### 3:05  Close (Slide 6)

`[SLIDE 6: close]`

"That is LeaseLens. It reads the document, flags what matters, and skips the
rest. Thank you for watching."

---

Tips: record at 1080p, move the cursor slowly, and pause for half a second after
each click so the panel can update. Keep it as one continuous recording. If you
misspeak, redo that one clip; the sections stand on their own.
