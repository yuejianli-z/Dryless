# Cross-platform README Assets

This directory contains documentation-only assets. Nothing under `docs/` is
loaded by the macOS app at runtime.

## Shared portrait

- `shared/readme-demo-person-original.jpg`: original portrait used to crop and
  annotate the README-only monitoring illustration.
- `shared/readme-demo-person-16x9-crop.jpg`: the 16:9 crop used for the macOS
  documentation preview. It is a framing reference, not an app asset.

Source: [Woman looking at the camera](https://unsplash.com/photos/woman-looking-at-the-camera--wTtFwEfvZo)
by Marek Pospisil on Unsplash, published under the
[Unsplash License](https://unsplash.com/license). The license permits free
commercial and non-commercial use and modification; attribution is not
required, but this source credit should remain with README material. Do not
sell the unmodified image separately or use it to create a competing image
service.

## README integration notes

1. Treat the portrait as README artwork only. Do not bundle it into the Windows
   or macOS runtime and do not use it as a camera fallback.
2. Keep a front-facing, webcam-like composition where the face fills the frame
   and both eyes remain unobscured.
3. Landmarks must follow the actual eyelids after the final crop. Use small,
   restrained sage-green nodes and thin lines; avoid a generic oval overlay.
4. Keep the source attribution and Unsplash License link next to the final
   README images or in the repository asset-credit section.

## Final interface screenshots

`docs/images/windows/` and `docs/images/macos/` contain the twelve final native-app screenshots: Monitor, Stats, and Settings in English and Simplified Chinese. The monitoring screenshots use the credited portrait above; the other UI is captured from each platform's app.
