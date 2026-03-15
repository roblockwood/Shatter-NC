# License options (vs Unlicense)

**This project now uses AGPL v3.** See [LICENSE](../LICENSE) and the README.

The notes below were used when choosing a license. Unlicense is public-domain style: no conditions, no attribution required, no restrictions on use. These options add some limits.

---

## Attribution-only (still very permissive)

**MIT**  
- **Limits:** Must keep copyright notice and license text in copies. No warranty.
- **Use:** Commercial OK, closed-source OK, modify/sell/use freely.
- **Good for:** “Use it however you want, but give credit.”

**Apache 2.0**  
- **Limits:** Like MIT, plus: state changes if you distribute modified code, patent grant from contributors, no use of project trademarks.
- **Use:** Commercial OK, closed-source OK.
- **Good for:** Same as MIT but with patent clarity and change notice.

**BSD 2-Clause / 3-Clause**  
- **Limits:** Attribution and “don’t use authors’ names to endorse” (3-Clause adds a no-endorsement clause).
- **Use:** Same as MIT in practice.

---

## Share-alike (derivatives must stay open)

**GPL v2 or v3**  
- **Limits:** If you distribute a modified or combined work, you must provide source under GPL. Strong copyleft.
- **Use:** Commercial use OK, but shipping a closed-source product that includes GPL code generally means you must open your code (or not distribute that combination).
- **Good for:** “Improvements and combined works must stay open source.”

**AGPL v3**  
- **Limits:** Like GPL, plus: offering the program as a network service counts as “distribution,” so you must offer source to users of that service.
- **Good for:** “SaaS based on this must also be open (or you need a different license from us).”

---

## Restricting commercial use

**CC BY-NC (Creative Commons Attribution-NonCommercial)**  
- **Limits:** Non-commercial use only; attribution required. “Commercial” is not always sharply defined.
- **Caveat:** CC is aimed at content; for software, MIT + a custom “non-commercial only” clause is more common.

**Custom “non-commercial” or “personal/educational only”**  
- **Limits:** You write the terms (e.g. “Non-commercial use only,” “No commercial use without permission”).
- **Good for:** “Free for personal/shop use, come to us for commercial licensing.”

---

## Recommendation for Shatter-NC

- **If you only want to add light limits:** Use **MIT** or **Apache 2.0** — attribution and no warranty, no commercial or usage restrictions. README already mentioned these.
- **If you want to keep derivatives open:** Use **GPL v3** (or **AGPL v3** if you care about SaaS).
- **If you want to forbid commercial use without permission:** Use a custom license or MIT + a short “Non-commercial use only” clause (lawyer review recommended for custom terms).

Say which option you want (e.g. MIT, Apache 2.0, GPL-3.0) and we can replace `LICENSE` and update the README accordingly.
