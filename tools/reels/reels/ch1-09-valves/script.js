// Narration and metadata for reel 09. Facts: Chapter 1, p 3 of Cardiothoracic Surgery (2nd ed.).
// Note: 'which would threaten a new valve' is the reason for the infection check; the book lists the check without the reason.
export const script = {
  id: "ch1-09-valves", index: 9, total: 18,
  title: "Valve patients have their own checklist",
  kicker: "CV history · Valves", source: "Ch 1 · p 3",
  poster: { at: "angio", plus: 2.0 },
  sentences: [
    { id: "hook", text: "Valve patients / have their own checklist." },
    { id: "note", text: "Note the type / and degree of valve disease, / and the left ventricular function / from the echo." },
    { id: "shape", text: "Those facts shape both the operation / and the risk." },
    { id: "ask", text: "Ask about rheumatic disease / and endocarditis." },
    { id: "dmg", text: "Both can damage valves, / and both change the plan." },
    { id: "dent", text: "Make sure a dentist / has recently cleared the mouth. / Patients with no teeth / do not need one." },
    { id: "inf", text: "Check there is no active source of infection, / because infection threatens a new valve." },
    { id: "angio", text: "Check they have had an angiogram / if they are men over {45=forty-five}, / postmenopausal women, / have angina-type symptoms, / or multiple coronary risk factors." },
    { id: "disc", text: "And confirm the type of valve replacement / has been discussed." },
    { id: "rec", text: "Valve, history, teeth, infection, angiogram, choice." },
  ],
};
