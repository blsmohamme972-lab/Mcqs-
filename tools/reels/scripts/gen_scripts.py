"""Generates reels/<id>/script.js for reels 02-18 (narration + metadata). Edit the data here or the files directly."""
import json, os, sys

TOTAL = 18
R = {}

def reel(n, slug, title, kicker, source, poster, sentences, note=""):
    R[n] = dict(slug=slug, title=title, kicker=kicker, source=source, poster=poster, sentences=sentences, note=note)

reel(2, "angina", "Angina is not always chest pain", "CV history · Angina", "Ch 1 · p 2", ("grade", 3.0), [
    ("hook", "Angina is not always / a crushing chest pain."),
    ("classic", "The textbook picture is central, crushing pain, / spreading to the jaw / and down the left arm."),
    ("atyp", "But patients may describe heaviness, / indigestion, / pain only in the arm, neck or jaw, / nausea, / or just fatigue."),
    ("trig", "So ask what brings it on: / exertion, stress, / emotion, / and cold air."),
    ("rel", "And what relieves it: / rest, / or sublingual nitroglycerine."),
    ("spray", "Then count the spray: / how many times a day / do they need it?"),
    ("grade", "Finally, grade it. / The Canadian Cardiovascular Society scale / applies to angina only."),
    ("c12", "Class one: no angina / with ordinary activity. / Class two: slight limitation."),
    ("c34", "Class three: marked limitation. / Class four: angina on minimal exertion, / or at rest."),
    ("risk", "Classes three and four / carry increased risk."),
    ("rec", "Describe it, trigger it, relieve it, / count it, / grade it."),
])

reel(3, "breathlessness", "How breathless is the patient?", "CV history · Dyspnea", "Ch 1 · p 2", ("hf", 2.5), [
    ("hook", "How breathless is the patient, / and why?"),
    ("ask", "Start with exertional dyspnea / and classify it / on the New York Heart Association scale."),
    ("n12", "Class one: no limitation / during ordinary activity. / Class two: slight limitation."),
    ("n34", "Class three: marked limitation. / Class four: no physical activity / without symptoms."),
    ("hf", "Heart failure is defined / as class three or four."),
    ("both", "The same scale also grades angina."),
    ("prec", "Then look for other precipitants: / paroxysmal nocturnal dyspnea, / orthopnea, / palpitations."),
    ("cause", "Chest infections, / {COPD=C O P D}, / pulmonary embolism, / and drugs such as {β-blockers=beta-blockers} / can all contribute."),
    ("assoc", "Ask about associated symptoms: / peripheral edema, / palpitations, / wheeze, / and sputum."),
    ("relief", "And what helps: / {NTG=nitroglycerine}, / rest, / or sitting up."),
    ("rec", "Classify it. / Define failure at class three. / Then hunt for the cause."),
])

reel(4, "mi-pci", "When was the last heart attack?", "CV history · MI & PCI", "Ch 1 · pp 2–3", ("risk2", 2.0), [
    ("hook", "When was the last heart attack?"),
    ("doc", "For every previous infarction, / document the number, / the dates, / and the coronary anatomy."),
    ("chk", "Check the chart, / and look for Q waves / on the {EKG=E K G}."),
    ("risk1", "Surgical risk is higher / after a recent {STEMI=stemmy} / than after an {NSTEMI=en stemmy}."),
    ("risk2", "And it is highest early after the infarct, / falling after one week."),
    ("pci", "Now previous stents and angioplasty. / Note the left ventricular function / and coronary anatomy / from the angiography report."),
    ("pci2", "Record how many procedures, / when, / what type, / and the result."),
    ("fail", "Emergency surgery after a failed {PCI=P C I} / is high risk."),
    ("clop", "And after a recent {PCI=P C I}, / clopidogrel usually continues / for at least one month, / which can change how bypass is done."),
    ("rec", "Count, date, anatomy, timing. / Then the stent story."),
], note="Book p 2 prints 'non-ST segment elevation MI (STEMI)'; the second term is a typo for NSTEMI and is narrated as NSTEMI.")

reel(5, "chest-surgery", "A previous operation changes the next one", "CV history · Redo", "Ch 1 · p 2", ("ct", 2.0), [
    ("hook", "A previous operation / changes the next one."),
    ("find", "Find it three ways: / ask, / check the chart, / and look."),
    ("look", "Look carefully at the whole chest, / and the back, / for scars."),
    ("scar", "A scar is the quickest clue / when the history is vague."),
    ("risk", "Previous cardiac surgery / adds to operative mortality, / and needs several changes / to the standard approach."),
    ("incr", "That added risk is incremental, / on top of every other factor."),
    ("ct", "That is why most patients / should have a {CT=C T} of the chest."),
    ("why", "It shows how the aorta / and the right ventricle / sit behind the sternum."),
    ("graft", "And where the patent bypass grafts run."),
    ("why2", "Those relationships decide / how safely the chest can be reopened."),
    ("contrast", "The scan needs intravenous contrast."),
    ("report", "And always obtain the operative report: / it records what was done."),
    ("rec", "Scars. {CT=C T}. Contrast. Report."),
], note="Sentences 'why2' and 'report' give the purpose of the scan and report; the book states the items, not the purpose.")

reel(6, "syncope", "A black-out is not always the heart", "CV history · Syncope", "Ch 1 · p 3", ("arr", 2.0), [
    ("hook", "A black-out / is not always the heart."),
    ("nonc", "Think epilepsy, / {TIAs=T I As}, / low blood sugar, / or a vasovagal faint."),
    ("vv", "Vasovagal faints follow standing, / emotion, / coughing, / or passing urine."),
    ("cardiac", "True cardiac syncope / from aortic stenosis / is usually exertional."),
    ("arr", "If it happens sitting or lying, / think arrhythmia."),
    ("dizzy", "Dizziness is different: / it can come before a faint, / but it is fairly non-specific."),
    ("drugs", "Common culprits are drugs: / antianginals, / antihypertensives, / and diuretics, / causing postural hypotension."),
    ("low", "It can also reflect low cardiac output, / from failure, arrhythmia or ischemia, / or cerebrovascular disease."),
    ("diab", "And do not forget / diabetic autonomic neuropathy: / probably under-recognized."),
    ("rec", "When did it happen? / What were they doing? / What are they taking?"),
])

reel(7, "palpitations", "What does a palpitation feel like?", "CV history · Palpitations", "Ch 1 · p 3", ("grad", 2.0), [
    ("hook", "What does a palpitation / actually feel like?"),
    ("feel", "To the patient it may be skipped beats, / a racing heart, / an irregular rhythm, / or simply awareness of the heartbeat, / especially at night."),
    ("onset", "Then ask about onset and offset."),
    ("rapid", "Rapid onset and offset / suggests a paroxysmal arrhythmia: / it switches on and off."),
    ("grad", "Gradual onset and offset / suggests sinus tachycardia: / it fades in and out."),
    ("af", "Preoperative atrial fibrillation / may need ablation, / left atrial appendage ligation, / and warfarin."),
    ("edema", "Now swelling. / Peripheral edema can follow / changes in diuretic therapy, / weight gain, / or worse breathlessness."),
    ("quant", "It helps quantify the heart failure."),
    ("rec", "Ask what it felt like, / how it started and stopped, / and whether the ankles swell."),
])

reel(8, "arteriopathy", "Arteries elsewhere change the operation", "CV history · Risk factors", "Ch 1 · p 3", ("why", 2.5), [
    ("hook", "Arteries elsewhere / change the operation here."),
    ("ask", "Ask specifically about {TIAs=T I As}, / strokes, / claudication, / and vascular interventions."),
    ("tia", "A history of {TIAs=T I As} / warrants a carotid duplex / to exclude carotid disease."),
    ("why", "Because arteriopathy outside the heart / feeds the risk score, / changes the stroke and limb-ischemia risk / you quote at consent, / and influences the conduit and cannulation site."),
    ("rf", "Then the risk factors. / Some can be fixed in hospital: / smoking, cholesterol, obesity, / hypertension and diabetes."),
    ("irr", "Some cannot: / male sex, / age, / and family history."),
    ("precise", "Be precise. / Non-smoker / is not the same as / smoked {60=sixty} a day / and stopped two weeks ago."),
    ("rec", "Check the carotids. / Fix what can be fixed. / Be exact."),
])

reel(9, "valves", "Valve patients have their own checklist", "CV history · Valves", "Ch 1 · p 3", ("angio", 2.0), [
    ("hook", "Valve patients / have their own checklist."),
    ("note", "Note the type / and degree of valve disease, / and the left ventricular function / from the echo."),
    ("shape", "Those facts shape both the operation / and the risk."),
    ("ask", "Ask about rheumatic disease / and endocarditis."),
    ("dmg", "Both can damage valves, / and both change the plan."),
    ("dent", "Make sure a dentist / has recently cleared the mouth. / Patients with no teeth / do not need one."),
    ("inf", "Check there is no active source of infection, / because infection threatens a new valve."),
    ("angio", "Check they have had an angiogram / if they are men over {45=forty-five}, / postmenopausal women, / have angina-type symptoms, / or multiple coronary risk factors."),
    ("disc", "And confirm the type of valve replacement / has been discussed."),
    ("rec", "Valve, history, teeth, infection, angiogram, choice."),
], note="'which would threaten a new valve' is the reason for the infection check; the book lists the check without the reason.")

reel(10, "history-flags", "Ask the question twice", "Systems · Past history", "Ch 1 · p 4", ("hip", 2.0), [
    ("hook", "Ask the question twice."),
    ("ask", "Any other medical problems? / Ever in hospital / for anything other than the heart? / Any operations, ever?"),
    ("why", "Be persistent: / patients often forget / important chronic illnesses and operations."),
    ("rt", "Previous chest radiotherapy / means a {CT=C T} scan, / because the aorta may be calcified."),
    ("ca", "Malignant disease needs careful evaluation: / in most cases, / metastatic spread is a relative contraindication / to cardiac surgery."),
    ("thy", "Thyroid disease may dictate / the choice of antiarrhythmic."),
    ("hip", "A hip replacement means / a pillow between the legs when transferring, / because adducting the hip / can dislocate it."),
    ("blood", "Blood dyscrasias, / thrombocytopenia, factor deficiencies, thrombophilias, / need a hematologist."),
    ("dm", "And diabetes has its own pre-op plan."),
    ("rec", "Every flag has an action."),
])

reel(11, "medications", "Every drug has a clock", "Systems · Medications", "Ch 1 · p 4", ("war", 2.0), [
    ("hook", "Every drug has a clock."),
    ("cont", "Antianginals and {β-blockers=beta-blockers} / continue until surgery."),
    ("after", "Afterwards, antianginals stop; / {β-blockers=beta-blockers} return / as pressure and rhythm allow."),
    ("ace", "{ACE=ace} inhibitors stop / {24–48=twenty-four to forty-eight} hours before, / to avoid profound peripheral dilatation / afterwards."),
    ("asa", "Aspirin and clopidogrel: / many surgeons stop them / {5–10=five to ten} days before, / because they increase bleeding."),
    ("asa2", "But ischemic risk rises slightly, / so high-risk patients, / such as recent {PCI=P C I} / or a tight left main, / may continue."),
    ("war", "Warfarin stops five days before. / If thromboembolic risk is high, / admit early for intravenous heparin."),
    ("ster", "Steroids: above five milligrams of prednisone daily, / give hydrocortisone cover / from the premedication, / to avoid an Addisonian crisis."),
    ("dm", "Long-acting hypoglycemics / are withheld on the morning of surgery, / with an insulin sliding scale if needed."),
    ("rec", "Continue, stop, or decide: / know the clock for each."),
])

reel(12, "allergies", "Allergies that change the operation", "Systems · Allergies", "Ch 1 · p 4", ("hit", 2.0), [
    ("hook", "Allergies: / the ones that change the operation."),
    ("take", "Take every drug, dose and regimen, / and every allergy: / drugs, iodine, contrast, / and fish."),
    ("why1", "Fish matters because protamine / is made from salmon sperm."),
    ("why2", "On bypass, the blood is anticoagulated with heparin, / and protamine reverses it at the end."),
    ("latex", "Latex allergy means changing the equipment, / so warn the operating room."),
    ("hit", "Heparin-induced thrombocytopenia / is the opposite problem: / heparin itself is the culprit."),
    ("alt", "Those patients may need a heparin-free bypass / with bivalirudin or argatroban, / which mandates careful pre-planning."),
    ("iod", "Iodine and contrast allergies / matter for every scan / and angiogram that follows."),
    ("rec", "Fish, latex, heparin, contrast: / four allergies, four plans."),
], note="'On bypass ... protamine reverses it' and 'every scan and angiogram that follows' are supporting explanations from standard practice; the book page lists the allergies only.")

reel(13, "social-neuro", "Social history is part of the surgical plan", "Systems · Social & neuro", "Ch 1 · p 5", ("alc", 2.0), [
    ("hook", "Social history / is part of the surgical plan."),
    ("jw", "Jehovah's Witness patients / do not accept blood / or blood products, / and some refuse cell salvage."),
    ("jw2", "Identify them early, / counsel them, / document their preferences, / and aim for a hematocrit above forty percent."),
    ("epo", "Several weeks of erythropoietin / may be indicated."),
    ("alc", "Heavy or binge drinkers / risk alcohol withdrawal."),
    ("hal", "Avoid haloperidol: / it lowers the seizure threshold / and prolongs the {QT=Q T} interval."),
    ("diaz", "Prescribe diazepam, / two milligrams orally every eight hours, / with thiamine and folate."),
    ("alone", "If the patient lives alone, / plan rehabilitation."),
    ("stick", "If they use a stick or frame, / involve physiotherapists early, / because sternal union may be compromised / even if mobility is not."),
    ("neuro", "And ask about {TIAs=T I As}, strokes / and residual deficit, / and identify dementia: / advanced dementia / is a contraindication to cardiac surgery."),
    ("rec", "Blood, alcohol, home, brain."),
])

reel(14, "chest-gut", "A cold can cancel the operation", "Systems · Chest & gut", "Ch 1 · p 5", ("gi", 2.0), [
    ("hook", "A cold can cancel the operation."),
    ("uri", "An active upper respiratory tract infection / is sufficient reason to cancel, / so ask about cough, colds / and sputum."),
    ("uri2", "If you suspect one, / measure the temperature, / {C-reactive=C reactive} protein / and white cell count, / and get a chest X-ray."),
    ("copd", "Assess {COPD=C O P D} / by asking about admissions, / inhalers, / nebulizers / and home oxygen."),
    ("pft", "If breathlessness dominates, / get lung function tests, / including blood gases."),
    ("gi", "Now the gut. / Cardiac surgery carries a risk of / upper G I bleeding from peptic ulcers, / prolonged ileus, / and flares of pancreatitis or cholecystitis."),
    ("ask", "So ask about dyspepsia, / ulcers / and pancreatitis."),
    ("ppi", "Start every patient on a proton pump inhibitor."),
    ("nsaid", "Flag the drug chart: / no {NSAIDs=en seds} in at-risk patients, / and give aspirin enteric-coated, / with food."),
    ("rec", "Lungs: infection and {COPD=C O P D}. / Gut: ask, protect, avoid {NSAIDs=en seds}."),
])

reel(15, "renal", "The kidneys can delay the operation", "Systems · Renal", "Ch 1 · p 5", ("cath", 2.0), [
    ("hook", "The kidneys can delay the operation."),
    ("check", "Check the notes for renal dysfunction."),
    ("acute", "If there is an acute deterioration, / it may be worth delaying surgery / to optimize."),
    ("opt", "Stop nephrotoxic drugs, / including {ACE=ace} inhibitors and {NSAIDs=en seds}, / start intravenous fluids with careful balance, / and sometimes dialyze."),
    ("dial", "Dialysis patients should be dialyzed / the morning of surgery, / or the night before."),
    ("cath", "Cardiac catheterization adds its own risk."),
    ("cath2", "Fasting leaves the patient hypovolemic, / and the contrast is nephrotoxic."),
    ("cath3", "So prescribe intravenous fluid / if renal function is borderline, / and consider intravenous acetylcysteine / before contrast studies."),
    ("pros", "And if the history suggests prostatic enlargement, / warn the patient / they may need a suprapubic catheter."),
    ("rec", "Protect, hydrate, dialyze, warn."),
])

reel(16, "short-exam", "The short examination", "Examination · Short exam", "Ch 1 · p 6", ("st3", 2.0), [
    ("hook", "Eight steps / make the short examination."),
    ("purpose", "Its purposes: / find disease that needs investigating, / help plan the surgery, / and spot problems that may delay recovery."),
    ("short", "For the average elective patient, / a shortened version is sufficient."),
    ("st1", "One: pulse, rate and rhythm. / Two: blood pressure."),
    ("st2", "Three: jugular venous pressure, / with the patient at {45°=forty-five degrees}."),
    ("st3", "Four: auscultate the heart sounds, / the carotids, / and the breath sounds, / and look for scars."),
    ("st4", "Five: the abdomen: / tenderness, hernias, / organomegaly, scars."),
    ("st5", "Six: feel the peripheral pulses, / including the abdominal aorta."),
    ("st6", "Seven: assess pedal edema. / Eight: assess the conduits, / the vessels that may become grafts."),
    ("rec", "Pulse, pressure, veins, / chest, abdomen, pulses, edema, conduits."),
], note="'the vessels that may become grafts' explains 'conduits' (standard meaning in bypass surgery).")

reel(17, "inspection-hands", "Examine from the end of the bed", "Examination · Inspection", "Ch 1 · p 6", ("osler", 2.0), [
    ("hook", "Examine from the end of the bed."),
    ("gen", "Is the patient comfortable at rest, / or requiring oxygen? / Well, or moribund? / Obese, or cachectic?"),
    ("syn", "Look for features of Down's syndrome, / which suggests an atrial or ventricular septal defect, / and Marfan syndrome, / which suggests aortic aneurysm, dissection / and incompetence."),
    ("pos", "Then position the patient at {45°=forty-five degrees}."),
    ("hands", "Now the hands and forearms. / Nicotine staining."),
    ("ie", "And the stigmata of endocarditis: / splinter hemorrhages."),
    ("osler", "Osler's nodes: / tender lumps in the fingertip pulps."),
    ("jane", "Janeway lesions: / red macules on the palms / or the flexor aspects of the wrists."),
    ("xan", "Tendon xanthomas. / And petechiae, / which may be present in infective endocarditis."),
    ("rec", "Bed-end, syndromes, hands: / what the surface says about valves and aorta."),
])

reel(18, "pulse-bp-face", "Pulse, pressure and face", "Examination · Signs", "Ch 1 · p 6", ("face", 2.0), [
    ("hook", "Pulse, pressure and face / each point to a diagnosis."),
    ("pulse", "Rate and rhythm at the radial pulse. / Character and volume / at the brachial or carotid."),
    ("as", "Aortic stenosis classically gives / a slow-rising, thready pulse."),
    ("ai", "Aortic incompetence gives / a large-volume bounding pulse."),
    ("bp1", "Blood pressure: / a systolic above {180=one hundred and eighty} / should be treated with nifedipine, / ten milligrams sublingually, / before surgery."),
    ("bp2", "A wide pulse pressure suggests aortic incompetence."),
    ("bp3", "Use a broad cuff for large arms, / or the pressure is underestimated."),
    ("bp4", "Check both arms / if you suspect aortic dissection / or coarctation."),
    ("face", "The face: / a malar flush, / cyanosis in a butterfly distribution, / is characteristic of mitral stenosis."),
    ("eyes", "In the eyes: / jaundice from hemolysis with prosthetic valves, / xanthelasma and corneal arcus with hyperlipidemia, / and Roth spots in endocarditis."),
    ("rec", "Slow pulse, wide pressure, malar flush: / three signs, three valves."),
])

def js(s): return json.dumps(s, ensure_ascii=False)

for n, r in R.items():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reels", f"ch1-{n:02d}-{r['slug']}")
    os.makedirs(d, exist_ok=True)
    rid = f"ch1-{n:02d}-{r['slug']}"
    lines = [f"// Narration and metadata for reel {n:02d}. Facts: {r['source'].replace('Ch 1 · ', 'Chapter 1, ')} of Cardiothoracic Surgery (2nd ed.)."]
    if r["note"]:
        lines.append(f"// Note: {r['note']}")
    lines.append("export const script = {")
    lines.append(f"  id: {js(rid)}, index: {n}, total: {TOTAL},")
    lines.append(f"  title: {js(r['title'])},")
    lines.append(f"  kicker: {js(r['kicker'])}, source: {js(r['source'])},")
    lines.append(f"  poster: {{ at: {js(r['poster'][0])}, plus: {r['poster'][1]} }},")
    lines.append("  sentences: [")
    for sid, text in r["sentences"]:
        lines.append(f"    {{ id: {js(sid)}, text: {js(text)} }},")
    lines.append("  ],")
    lines.append("};")
    path = os.path.join(d, "script.js")
    if os.path.exists(os.path.join(d, "reel.js")) or n == 1:
        pass
    open(path, "w").write("\n".join(lines) + "\n")
print("wrote", len(R), "scripts")
