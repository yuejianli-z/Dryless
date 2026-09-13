# Dryless UI fonts

These are renamed static subset derivatives, distributed under the SIL Open Font License 1.1 alongside their original license files. Original copyright and license metadata is retained inside each font.

- **Dryless Sans** derives from the official Inter variable font: https://github.com/rsms/inter . It supplies Latin letters, digits, and punctuation.
- **Dryless CJK** derives from Noto Sans SC. It supplies 4,303 Unicode characters, including common Chinese characters and the current Dryless interface text. Noto source project: https://github.com/notofonts/noto-cjk . Its accompanying license is also published at https://github.com/google/fonts/tree/main/ofl/notosanssc .
- The installed CJK source retains the following original notice: © 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'. Its version string is `Version 2.04;241114210130;non-release`.
- Static weights: **Regular 400**, **Medium 500**, **SemiBold 600**. No variable font tables remain. Font family names were changed to avoid system-font collisions and to respect Inter's reserved font name.
- Font selection: `Dryless Sans`, then `Dryless CJK`, then `Microsoft YaHei UI` for any character outside the bundled subset. Load the TTF files before constructing widgets.
- Keep `Inter-OFL.txt`, `NotoSansSC-OFL.txt`, and this notice together with the fonts. The original authors do not endorse this application.

The assets occupy about 4.15 MB in total. `manifest.json` records the individual sizes and SHA-256 checksums. Development source generation is in the adjacent `build_fonts.py` staging script.
