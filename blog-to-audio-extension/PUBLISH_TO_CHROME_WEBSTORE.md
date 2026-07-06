# How to Publish Your Chrome Extension to the Chrome Web Store
### A Complete Step-by-Step Guide — No Questions Left Unanswered

---

## What You Will Have at the End
Your "Text to Audio Online" extension will be live on the Chrome Web Store. Anyone in the world can search for it and install it for free.

---

## Things You Need Before Starting

| What | Details |
|------|---------|
| Your zip file | Already at `C:\Users\HI\Documents\blog-to-audio-extension.zip` |
| A Google account | The same Gmail you use normally |
| A debit or credit card | For the one-time $5 fee |
| 2 screenshots | We will create these in Step 2 |
| 30–45 minutes | To complete everything |

---

---

# STEP 1 — Register as a Chrome Developer (Pay the $5 Fee)

This is a one-time payment. You pay it once and never again, even if you publish 100 extensions.

### 1.1 — Open the Developer Console

1. Open **Google Chrome** on your computer
2. In the address bar at the top, type exactly this and press **Enter**:
   ```
   https://chrome.google.com/webstore/devconsole
   ```
3. You will see a Google sign-in page

### 1.2 — Sign In with Your Google Account

1. Type your **Gmail address** and click **Next**
2. Type your **password** and click **Next**
3. If it asks for 2-step verification, complete it

### 1.3 — Pay the Registration Fee

1. After signing in, you will see a page that says **"Pay a one-time developer registration fee"**
2. Click the blue **"Pay"** button
3. A payment popup will appear
4. Enter your **card number**, **expiry date**, and **CVV** (the 3-digit number on the back)
5. Enter your **name as it appears on the card**
6. Click **"Buy"** or **"Pay $5.00"**
7. Wait a few seconds — the payment will process
8. You will be taken to the **Chrome Web Store Developer Dashboard**

> If you already paid in the past and see the dashboard directly, skip to Step 2.

### 1.4 — Accept the Developer Agreement

1. A popup may appear asking you to accept the **"Chrome Web Store Developer Agreement"**
2. Read it if you want, then click **"I Agree"** or **"Accept"**
3. You are now a registered Chrome developer

---

---

# STEP 2 — Take Screenshots of Your Extension

Google requires a minimum of **2 screenshots**. These are shown on your extension's store page so people can see what it looks like before installing.

### 2.1 — Open Your Extension

1. Click the **puzzle piece icon** (🧩) in the top-right corner of Chrome
2. Find **"Text to Audio Online"** in the list
3. Click it to open the popup
4. You should see the extension UI with the URL field and "Convert to Audio" button

### 2.2 — Take Screenshot 1 (The Main Popup)

This screenshot shows the extension popup as it looks when first opened.

1. Make sure the extension popup is open and visible on screen
2. Press **Windows key + Shift + S** at the same time
3. Your screen will dim slightly and a toolbar appears at the top
4. Click the **first icon** (rectangular selection)
5. Click and drag to select just the extension popup area
6. Release the mouse — the screenshot is copied to your clipboard
7. Open **Paint** (search for it in the Start menu)
8. Press **Ctrl + V** to paste the screenshot
9. Click **File → Save As**
10. Change "Save as type" to **PNG**
11. Name it: `screenshot-1-popup.png`
12. Save it to your **Desktop**

### 2.3 — Take Screenshot 2 (After Converting — Showing the Audio Player)

This screenshot shows the extension after it has converted a blog, with the audio player visible.

1. Open any blog post in Chrome (for example: https://blog.hubspot.com or any article)
2. Click your **Text to Audio** extension icon
3. The blog URL should auto-fill in the URL box
4. Click **"Convert to Audio"** and wait for it to finish
5. You will see the audio player and the "Download MP3" button appear
6. Now take a screenshot of this state using the same steps as above (Windows + Shift + S)
7. Save it as `screenshot-2-result.png` on your **Desktop**

### 2.4 — Resize Screenshots to the Correct Size

Google requires screenshots to be exactly **1280x800** or **640x400** pixels. Your screenshots might be a different size. Here is how to resize them for free:

1. Open your browser and go to: https://www.resizepixel.com
2. Click **"Upload Image"** and upload `screenshot-1-popup.png`
3. Set **Width** to `1280` and **Height** to `800`
4. Click **"Apply"** and then **"Download"**
5. Save the downloaded file back to your Desktop (replace the old one)
6. Repeat for `screenshot-2-result.png`

> You now have 2 correctly-sized screenshots ready for upload.

---

---

# STEP 3 — Go to the Developer Console and Create a New Item

### 3.1 — Open the Developer Console

1. In Chrome, go to:
   ```
   https://chrome.google.com/webstore/devconsole
   ```
2. Make sure you are signed in (you should see your name or email in the top right)
3. You will see your **Developer Dashboard** — it may be empty if this is your first extension

### 3.2 — Click "New Item"

1. Look for a button in the top-right area that says **"New Item"**
2. Click it
3. A file upload box will appear saying **"Upload a zip file"**

### 3.3 — Upload Your Extension Zip File

1. Click **"Choose file"** or **"Browse"**
2. A file explorer window opens
3. Navigate to: `C:\Users\HI\Documents\`
4. Find the file called `blog-to-audio-extension.zip`
5. Click on it to select it
6. Click **"Open"**
7. The file will start uploading — wait 10–20 seconds
8. When done, you will be taken to a page with many fields to fill in

> If you see an error like "Invalid manifest" — contact Claude Code to fix it.

---

---

# STEP 4 — Fill In the Store Listing

This is the page people see when they find your extension. Fill in every field exactly as shown below.

### 4.1 — Extension Name

This field may already be filled in from your manifest. If not, type:
```
Text to Audio Online
```

### 4.2 — Short Description

This appears under your extension name in search results. It must be under 132 characters.
```
Convert any blog or article URL into an MP3 audio file instantly with one click.
```

**How to enter it:**
1. Click the "Short description" box
2. Type or paste the text above
3. Check that the character counter does not go red

### 4.3 — Detailed Description

This is the full description shown on your extension's page. Copy and paste this exactly:

```
Text to Audio Online lets you convert any blog post or article into an audio file in seconds — directly from your browser.

HOW TO USE:
1. Go to any blog or article in Chrome
2. Click the "Text to Audio Online" extension icon in your toolbar
3. The blog URL is automatically detected and filled in
4. Click "Convert to Audio"
5. Listen to the audio directly inside the popup
6. Click "Download MP3" to save the audio file to your computer

FEATURES:
✅ Automatically detects the blog URL you are on
✅ Paste any URL or text manually
✅ Converts to high-quality MP3 audio
✅ Built-in audio player — listen without leaving the page
✅ One-click MP3 download
✅ Share feedback from within the extension
✅ Works with any English blog or article
✅ Free to use — no account needed

PERFECT FOR:
- Commuters who want to listen to articles on the go
- Students who prefer listening over reading
- Busy professionals who do not have time to read
- Anyone who wants to turn written content into a podcast-style audio

Your privacy is respected — we do not store your text or URLs. Read our privacy policy at: https://text-to-audio-online.vercel.app/privacy
```

**How to enter it:**
1. Click the "Detailed description" box
2. Press **Ctrl + A** to select all, then delete
3. Paste the text above using **Ctrl + V**

### 4.4 — Category

1. Find the dropdown that says **"Category"**
2. Click on it
3. Select **"Productivity"** from the list

### 4.5 — Language

1. Find the **"Language"** dropdown
2. Select **"English"**

---

---

# STEP 5 — Upload Your Screenshots

### 5.1 — Find the Screenshots Section

1. Scroll down the listing page until you see **"Screenshots"**
2. You will see a box with a dashed border and a "+" button or "Add screenshot" button

### 5.2 — Upload Screenshot 1

1. Click **"Add screenshot"** or the **"+"** button
2. A file picker opens
3. Navigate to your **Desktop**
4. Select `screenshot-1-popup.png`
5. Click **"Open"**
6. Wait for it to upload — you will see a thumbnail appear

### 5.3 — Upload Screenshot 2

1. Click **"Add screenshot"** again
2. Select `screenshot-2-result.png`
3. Click **"Open"**
4. Wait for the thumbnail to appear

### 5.4 — Check the Order

- The first screenshot should be the main popup (screenshot 1)
- The second should show the audio player result (screenshot 2)
- If they are in the wrong order, drag and drop them to swap

---

---

# STEP 6 — Upload Your Store Icon

The store icon is the image shown next to your extension name in search results.

### 6.1 — Find the Store Icon Section

1. Scroll to find the section called **"Store icon"**
2. It requires a **128x128 pixel PNG** image

### 6.2 — Upload the Icon

1. Click **"Upload store icon"** or the upload button in that section
2. Navigate to: `C:\Users\HI\Documents\blog-to-audio-extension\icons\`
3. Select `icon128.png`
4. Click **"Open"**
5. The icon will appear as a small preview

> If the icon looks too plain (it is a solid purple square), you can design a better one for free at https://www.canva.com — create a 128x128 image with a microphone or sound wave design, download as PNG, and upload it here.

---

---

# STEP 7 — Fill In the Privacy Section

**This section is mandatory.** Google will automatically reject your extension if you skip it.

### 7.1 — Find the Privacy Practices Section

1. Scroll down until you see **"Privacy practices"**
2. You will see two subsections: **"Privacy policy"** and **"Permissions"**

### 7.2 — Add Your Privacy Policy URL

1. In the **"Privacy policy URL"** field, paste this link exactly:
   ```
   https://text-to-audio-online.vercel.app/privacy
   ```
2. Press **Tab** or click elsewhere — the field should turn green if the URL is valid

### 7.3 — Justify Your Permissions

Google will ask you to explain why you need each permission your extension uses. Here is what to write for each one:

**For the `tabs` permission:**
1. Find the row that says **"tabs"**
2. In the justification box next to it, type:
   ```
   Used to read the URL of the current active tab so it can be automatically filled into the extension popup, saving the user from having to copy and paste the blog URL manually.
   ```

**For the host permission `https://text-to-audio-online.vercel.app/*`:**
1. Find this row in the permissions list
2. In the justification box, type:
   ```
   This is the extension's own API server. It is used to fetch text content from blog URLs and convert that text into an MP3 audio file using text-to-speech technology.
   ```

---

---

# STEP 8 — Set Visibility and Distribution

### 8.1 — Find the Distribution Section

1. Scroll down to find **"Distribution"** or **"Visibility"**

### 8.2 — Set Visibility to Public

1. You will see options like **"Public"**, **"Unlisted"**, and **"Private"**
2. Select **"Public"**
   - Public = Anyone can find and install it by searching the Chrome Web Store
   - Unlisted = Only people with the direct link can install it
   - Private = Only you can install it

### 8.3 — Set Countries

1. Under distribution regions, leave it set to **"All countries and regions"**
2. This makes your extension available worldwide

---

---

# STEP 9 — Check Everything and Submit

### 9.1 — Check for Errors

1. Scroll back to the top of the page
2. Look for any **red warnings** or **orange alerts**
3. If you see any, click on them to see what is missing and fix it
4. Common warnings:
   - "Screenshots required" → Go back to Step 5
   - "Privacy policy required" → Go back to Step 7
   - "Description is too short" → Go back to Step 4.3

### 9.2 — Save as Draft First

1. Before submitting, click **"Save Draft"**
2. This saves everything you have filled in so far
3. Come back and review it once more

### 9.3 — Preview Your Listing

1. Look for a **"Preview"** button or link
2. Click it to see how your extension will look in the Chrome Web Store
3. Check that the name, description, screenshots, and icon all look correct

### 9.4 — Submit for Review

1. When you are happy with everything, click the **"Submit for review"** button
2. It may ask: **"Are you sure you want to submit?"** — click **"Submit"**
3. The status will change to **"Pending Review"**

> You will NOT receive an immediate answer. Google reviews it manually.

---

---

# STEP 10 — Wait for Approval

### What Happens After You Submit

| Time | What Happens |
|------|-------------|
| Immediately | Status = "Pending Review" |
| Within 24 hours | Google starts reviewing it |
| 1–3 business days | Decision is made |
| If approved | Status = "Published" — it goes live immediately |
| If rejected | You get an email explaining exactly why |

### How to Check the Status

1. Go to: https://chrome.google.com/webstore/devconsole
2. You will see your extension listed with a status badge
3. Refresh the page every day to check

### What to Do If It Gets Rejected

1. You will receive an email from Google explaining the reason
2. Read the reason carefully
3. Fix the issue (come back to Claude Code and explain what they said)
4. Re-submit — there is no penalty for being rejected once

### Most Common Rejection Reasons and Fixes

| Rejection Reason | Fix |
|-----------------|-----|
| "Misleading description" | Remove any claims that are not 100% accurate |
| "Overly broad permissions" | Go to Claude Code — we can reduce the permissions |
| "Privacy policy not accessible" | Check that the privacy URL works in a browser |
| "Functionality does not work" | Test the extension again and report the issue to Claude Code |
| "Deceptive behaviour" | This happens if the description claims features that don't exist — remove them |

---

---

# After Publishing — How to Update Your Extension

Every time you want to make a change (fix a bug, add a feature, update the description):

### To Update the Extension Code

1. Come to **Claude Code** and describe the change you want
2. Claude Code will update the files and re-zip automatically
3. Go to: https://chrome.google.com/webstore/devconsole
4. Click on your extension
5. Click the **"Package"** tab on the left
6. Click **"Upload new package"**
7. Upload the new zip file from `C:\Users\HI\Documents\blog-to-audio-extension.zip`
8. Click **"Submit for review"**
9. Updates are usually approved in **1–2 days**

### To Update Only the Description or Screenshots (No Code Change)

1. Go to: https://chrome.google.com/webstore/devconsole
2. Click your extension
3. Click **"Store listing"** on the left
4. Edit whatever you want to change
5. Click **"Save draft"** then **"Submit for review"**

---

---

## Quick Reference — All Important Links

| What | Link |
|------|------|
| Developer Console | https://chrome.google.com/webstore/devconsole |
| Privacy Policy (your extension) | https://text-to-audio-online.vercel.app/privacy |
| Your website | https://text-to-audio-online.vercel.app |
| Free screenshot resizer | https://www.resizepixel.com |
| Free icon designer | https://www.canva.com |

## Your File Locations

| What | Location |
|------|---------|
| Extension folder | `C:\Users\HI\Documents\blog-to-audio-extension` |
| Zip file to upload | `C:\Users\HI\Documents\blog-to-audio-extension.zip` |
| Icon file | `C:\Users\HI\Documents\blog-to-audio-extension\icons\icon128.png` |

---

*Built with Claude Code. For any changes or issues, open Claude Code and describe what you need.*
