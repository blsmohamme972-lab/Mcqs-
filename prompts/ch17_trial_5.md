# Chapter 17 — five trial image prompts

**المصدر:** Cardiothoracic Surgery, 2nd ed. (Chikwe 2013), Chapter 17 Chest trauma،
صفحات الكتاب 818–823. كل عنصر في الصورة مرتبط بجملة من الكتاب (العمود الأول حرفي).

**العالم الثابت** (نفس المشهد السابق — tension pneumothorax): المبنى = القفص الصدري،
الطوابق = المسافات الضلعية، عوارض السقف = الأضلاع، درابزين السطح = الترقوة،
الرئة = بالون وردي بوجه، القلب = قلب أحمر بوجه، البطل = نفس الإطفائي، السبّاك = نفس السبّاك.

**كتلة الأسلوب** (تُلصق أول كل برومبت — من `docs/style-guide.md`):

```
Style: cute chibi characters with big expressive eyes, glossy soft-3D vector look,
rounded shapes, vibrant neon accents (hot pink #FF3D7F, violet #8B5CF6, cyan #22D3EE)
on a deep dark navy background, soft rim lighting and subtle glow, clean composition,
playful and charming, family-friendly. 16:9 landscape, every element clearly separated
with breathing room. NO text, NO letters, NO numbers, NO labels anywhere.
```

**Negative prompt** (لكل الصور): `text, letters, words, numbers, labels, watermark, logo,
realistic gore, blood splatter, photorealistic anatomy, cluttered background, extra limbs, distorted faces`

---

## 1. Flail chest — p822

| نص الكتاب | الرمز | region id |
|---|---|---|
| fracture of three or more ribs in a row, with two or more fractures in each rib | ثلاث عوارض متتالية، كل واحدة مكسورة في مكانين، فتنفصل "جزيرة" من الجدار | `island` |
| the chest wall 'island' exhibits paradoxical motion with respiration | المبنى ينتفخ للخارج والجزيرة تُشفط للداخل (أسهم متعاكسة) | `paradox` |
| underlying pulmonary contusion | بالون الرئة خلف الجزيرة عليه كدمات بنفسجية | `contusion` |
| dyspnea, hemoptysis, pain, respiratory splinting, respiratory distress | الرئة تلهث، تسعل قطرات حمراء صغيرة، تحضن نفسها بتصلّب | `symptoms` |
| Usually obvious on clinical exam: can confirm with CXR and chest CT | طبيب بعدسة مكبرة + كاميرا أشعة + حلقة CT | `diagnosis` |
| Mechanical ventilation if the patient is in distress | جهاز منفاخ (بيلوز) موصول بالرئة | `ventilator` |
| pain control with narcotics, PCA, rib blocks, or epidural analgesia | ممرضة بيد الرئة زر تحكم بالألم (PCA) | `analgesia` |
| limit fluids … capillary leak | صنبور ماء مُغلق بإحكام فوق رئة إسفنجية تقطر | `fluids` |
| No clear data on early fixation … external plate fixation can help wean off ventilation | عامل يثبّت لوحاً معدنياً على الجزيرة وهو يهز كتفيه | `plate` |
| The flail segment will often fibrose with time | لبلاب أخضر ينمو فوق الجزيرة ويثبّتها + ساعة رملية | `fibrosis` |

**القصة:** ثلاث عوارض انكسرت كل منها مرتين فانفصلت جزيرة من الجدار؛ كلما تنفس المبنى شُفطت للداخل بعكس الباقي.
خلفها الرئة مكدومة تلهث وتسعل. العلاج داعم: منفاخ، زر الألم، إغلاق صنبور السوائل، ولوح معدني ربما؛ ومع الوقت يغطيها اللبلاب ويثبّتها.

```
[STYLE BLOCK]
SETTING: the same cartoon apartment building shaped like a rib cage, front cross-section,
floors separated by curved rib-shaped beams. Focus on the right outer wall.
ELEMENTS:
1. Three consecutive curved rib-beams on the right wall, each snapped in TWO places, so a
   loose rectangular "island" of wall floats free from the rest of the building.
2. The building visibly inflating outward (outward arrows) while the loose island is
   sucked INWARD (inward arrows), clearly moving opposite to the rest of the wall.
3. Behind the island, the pink lung-balloon character with purple bruise patches.
4. The lung gasping, wincing in pain, hugging itself stiffly, coughing tiny red droplets.
5. A doctor peering through a big magnifying glass, next to a boxy X-ray camera and a
   glowing donut-shaped CT ring.
6. A friendly bellows machine connected by a tube to the lung, pumping air.
7. A nurse handing the lung a small remote with one big glowing button (pain relief).
8. A water tap above the lung turned tightly OFF, the lung looking like a damp sponge.
9. A handyman bolting a shiny metal plate across the island, shrugging uncertainly.
10. Green ivy vines growing over the island's edges, holding it in place, beside an hourglass.
```

---

## 2. Hemothorax — p823

| نص الكتاب | الرمز | region id |
|---|---|---|
| Causes: chest wall injury, lung parenchymal laceration, bronchial artery injury, intercostal vessel injury, major thoracic vascular injury | خمسة تسريبات حمراء (عصير كرز) في الشقة: جدار مكسور، بالون رئة ممزق، أنبوب صغير، أنابيب على طول العوارض، أنبوب رئيسي ضخم | `causes` |
| Chest radiograph diagnostic | مصوّر الأشعة مُرحَّب به هذه المرة، يلتقط الصورة | `cxr` |
| tube thoracostomy … wide-bore, at least a 36F, tube | السبّاك يحمل خرطوماً عريضاً جداً | `widebore` |
| in the 5th or 6th intercostal space in the midaxillary line | يركّبه في الجدار الجانبي بين الطابقين 5 و6 | `site` |
| directing the tube posteriorly | فوهة الخرطوم متجهة للأسفل وللخلف — حيث يتجمع السائل | `posterior` |
| Bleeding ceases in 80–90% of cases | عشر قطرات، تسع منها متجمدة متوقفة | `ceases` |
| Indications for surgery: immediate blood loss of >1L | زجاجة لتر كاملة تفيض فوراً | `oneliter` |
| or bleeding continues in excess of 100mL/h for 4h or more | ساعة حائط بأربعة أكواب صغيرة تمتلئ واحداً كل ساعة، والجراح يصل | `fourhours` |
| Blunt trauma to esophagus and thoracic duct rare | وحيد قرن نادر يمر بجانب أنبوب المريء | `rare` |

**القصة:** خمسة تسريبات تملأ الشقة بعصير أحمر؛ هذه المرة مصوّر الأشعة هو من يشخّص. السبّاك يركّب خرطوماً عريضاً بين الطابقين 5 و6
موجهاً للأسفل وللخلف (السائل يهبط — عكس الهواء الذي يصعد). تسع من عشر قطرات تتوقف؛ لكن لتر دفعة واحدة، أو كوب كل ساعة لأربع ساعات، يستدعي الجراح.

```
[STYLE BLOCK]
SETTING: the same rib-cage apartment building, front cross-section; the right apartment's
floor is filling with glossy cherry-red juice (cartoon liquid, not gore).
ELEMENTS:
1. Five separate leaks pouring juice into the right apartment: a cracked outer wall, a small
   tear in the pink lung balloon, a thin red pipe, pipes running along the rib-beams,
   and one huge main pipe.
2. A cheerful X-ray photographer, welcomed with applause, snapping a picture.
3. The same plumber carrying a very wide, fat hose.
4. The plumber fitting the hose into the SIDE wall between the 5th and 6th floors.
5. The hose opening pointing DOWNWARD and BACKWARD into the pool of juice.
6. A row of ten juice drops in mid-air: nine frozen solid like ice, one still falling.
7. A one-litre bottle overflowing all at once.
8. A wall clock with four small cups beneath it, filling one after another, while a
   surgeon in scrubs hurries in through the door.
9. A rare sparkly unicorn trotting past a narrow food pipe at the back of the building.
```

---

## 3. Diaphragmatic injury — p823

| نص الكتاب | الرمز | region id |
|---|---|---|
| Blunt trauma, with acute intra-abdominal pressure can lead to laceration and disruption of the diaphragm | مصارع سومو يجلس على القبو فيضغط للأعلى، وأرضية المبنى (الحجاب) تتمزق | `sumo` |
| More common on the left side, as the liver serves as a barrier | جهة اليمين: كبد بني يحمل درعاً يحمي الأرضية؛ التمزق في جهة اليسار | `liver` |
| Often asymptomatic … May present late | قطة نائمة فوق التمزق + تقويم بأوراق متطايرة | `late` |
| Symptoms include dyspnea, abdominal pain, atypical chest pain, dysphagia, bowel obstruction | الرئة تلهث، شخصية تمسك بطنها، أخرى تختنق بلقمة، أمعاء ثعبانية معقودة | `symptoms` |
| CXR may demonstrate gastric bubble above the diaphragm | بالون المعدة يطفو صاعداً عبر التمزق إلى الطابق الأرضي من الصدر | `bubble` |
| Chest CT with IV and oral contrast helpful | حلقة CT؛ شخصية تشرب مشروباً متوهجاً وفي ذراعها محلول وريدي متوهج | `ct` |
| Diagnostic laparoscopy | كاميرا صغيرة على عصا تطل من نافذة صغيرة في القبو | `laparoscopy` |
| Treatment is primary repair … laparoscopically or thoracoscopically, or via a laparotomy or thoracotomy | خيّاطة تخيط الأرضية الممزقة، وأدوات تصلها من الأعلى ومن الأسفل | `repair` |

**القصة:** سومو يجلس على القبو فتتمزق الأرضية — من جهة اليسار، لأن الكبد يحمي اليمين بدرعه. قطة تنام فوق التمزق لأسابيع (لا أعراض، ظهور متأخر)،
ثم تصعد المعدة كفقاعة إلى الصدر. التشخيص: CT بمشروب ومحلول متوهجين، أو كاميرا من القبو؛ والعلاج خياطة الأرضية من فوق أو من تحت.

```
[STYLE BLOCK]
SETTING: the same rib-cage apartment building, now showing its floor (a dome-shaped
diaphragm floor) and the basement below it (the abdomen).
ELEMENTS:
1. A chubby sumo wrestler sitting heavily in the basement, pushing up; the LEFT side of
   the dome floor above him tearing open.
2. On the RIGHT side, a big brown liver character holding a round shield under the floor,
   protecting it (that side is intact).
3. A cat sleeping peacefully on the tear, with a wall calendar whose pages fly away.
4. Small characters with symptoms: the pink lung gasping, one holding its tummy, one
   struggling to swallow a big bite, a snake-like intestine tied in a knot.
5. A round stomach-balloon floating UP through the tear into the chest floor above.
6. A glowing donut-shaped CT ring; a character sipping a glowing drink with a glowing
   IV drip in its arm.
7. A tiny camera on a stick peeking in through a small round basement window.
8. A seamstress stitching the torn floor, with tools reaching in from above and below.
```

---

## 4. Emergency thoracotomy — p818–819

| نص الكتاب | الرمز | region id |
|---|---|---|
| Cardiac arrest or imminent cardiac arrest after penetrating trauma | فارس برمح (طعن) والقلب يكاد يتوقف | `penetrating` |
| Limited role in cardiac arrest in setting of blunt trauma | قفاز ملاكمة (رضّ) جالس جانباً، مستبعد | `blunt` |
| clamshell … rapid and excellent access … does not require sternal saw … incision of choice in the emergency room | صدفة محار عملاقة تفتح واجهة المبنى بالكامل، والمنشار مركون | `clamshell` |
| Cardiac tamponade is the commonest finding | القلب محبوس داخل بالون ماء منتفخ يعصره | `tamponade` |
| RV lacerations more commonly than LV lacerations | ضمادة كبيرة على الجهة اليمنى للقلب، صغيرة على اليسرى | `rv` |
| VSD is the commonest intracardiac injury | ثقب في الجدار الأوسط داخل القلب | `vsd` |
| the heart is empty from massive hemorrhage elsewhere: internal cardiac massage is more effective than external chest compressions | قلب فارغ ودلو فارغ؛ يدان تدلكان القلب مباشرة | `massage` |
| Do not stop to place lines, or anesthetize or intubate the patient | عدّاء يقفز فوق حواجز (أنبوب، محلول) دون توقف | `nostop` |
| At a minimum you need gloves, a scalpel, a scissors and suction | حزام أدوات: قفازات، مشرط، مقص، شفاط | `kit` |
| Stay calm, and communicate clearly | جراح هادئ كالراهب بجهاز لاسلكي وسط حشد متحمس | `calm` |

**القصة:** فارس يطعن والقلب على وشك التوقف — هنا نفتح؛ أما قفاز الملاكمة فدوره محدود. الصدفة العملاقة تفتح الصدر بلا منشار.
في الداخل: القلب محبوس في بالون ماء (tamponade)، ضمادته الكبرى على اليمين، وثقب في جداره الأوسط. إن كان فارغاً فالتدليك من الداخل.
لا تتوقف للحواجز، احمل أربع أدوات فقط، وابقَ هادئاً.

```
[STYLE BLOCK]
SETTING: the same rib-cage apartment building, its front being opened like a giant clam
shell in an emergency room.
ELEMENTS:
1. A small knight holding a lance near the building, the red heart character fainting.
2. A boxing glove character sitting on a bench to the side, left out.
3. A huge glossy clam shell opening the whole front of the building wide; an unused saw
   leaning against the wall nearby.
4. The red heart trapped inside a tight, bulging water balloon that squeezes it.
5. The heart wearing a BIG bandage on its right side and a tiny one on its left side.
6. A small round hole in the wall between the heart's two halves.
7. An empty bucket beside an empty-looking heart, and two gentle hands massaging the heart
   directly.
8. A runner leaping over small hurdles shaped like a tube and a drip bag without stopping.
9. A tool belt holding exactly four tools: gloves, a scalpel, scissors, a suction wand.
10. A calm, zen surgeon with a walkie-talkie, standing still amid an excited crowd.
```

---

## 5. Rib fracture — p822

| نص الكتاب | الرمز | region id |
|---|---|---|
| Common. 4th–9th ribs most commonly fractured | عوارض الطوابق من 4 إلى 9 مشققة (الأكثر شيوعاً) | `ribs49` |
| Associated with underlying lung, pleural, bronchial, and cardiac injuries | خلف العوارض المشققة: الرئة، والقلب، وأنبوب القصبة بضمادات | `underlying` |
| Lower rib fractures associated with renal, hepatic and splenic injuries | في القبو: حبة فاصوليا (كلية)، كبد، طحال — تصيبهم عوارض سفلية متساقطة | `lower` |
| Fracture of the 1st rib (or sternum or scapula) indicates major trauma | كرة هدم ضخمة كسرت عارضة الطابق الأول + عمود الواجهة (القص) + جناح الكتف (اللوح) | `first` |
| Management: adequate analgesia | ممرضة تدهن مرهماً مهدئاً | `analgesia` |
| May require regional nerve blocks | كهربائي يفصل سلكاً واحداً | `block` |
| Epidural very effective anesthesia with minimal complications | لمسة لطيفة على عمود المبنى الخلفي، والسكان ينامون بسلام | `epidural` |

**القصة:** الطوابق 4 إلى 9 هي التي تتشقق عادة، ومن خلفها قد تُصاب الرئة والقلب والقصبة؛ والعوارض السفلية تسقط على الكلية والكبد والطحال في القبو.
أما كسر الطابق الأول (أو القص أو اللوح) فيحتاج كرة هدم — أي رضّ شديد. العلاج مسكّن، وفصل سلك العصب، واللمسة الخلفية (epidural) الأكثر فعالية.

```
[STYLE BLOCK]
SETTING: the same rib-cage apartment building, front cross-section, all floors visible,
plus the basement (abdomen) below.
ELEMENTS:
1. The rib-beams of the middle floors (counting the 4th to the 9th from the top) cracked,
   the top three floors and the bottom ones intact.
2. Behind the cracked beams: the pink lung balloon, the red heart and a windpipe-tube
   character, each wearing small bandages.
3. In the basement, a kidney-bean character, a brown liver and a purple spleen dodging
   falling pieces of the lowest beams.
4. A giant wrecking ball that has smashed the TOP floor's beam, the central front pillar,
   and a shoulder-blade-shaped wing on the side of the building.
5. A nurse gently rubbing soothing glowing cream on the building.
6. An electrician snipping one single wire running along a beam.
7. A gentle glowing touch on the building's back column, and the residents sleeping calmly.
```

---

## مفتاح التجربة

بعد توليد الصور الخمس، أرسلها لي: أحدد مواضع الـ region ids على كل صورة (x, y, w, h)،
وأتحقق أن كل رمز في الجدول موجود وواضح قبل استخدامها في البطاقات والمحاضرات.
