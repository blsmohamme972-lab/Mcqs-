// Narration and metadata for reel 04. Facts: Chapter 1, pp 2–3 of Cardiothoracic Surgery (2nd ed.).
// Note: Book p 2 prints 'non-ST segment elevation MI (STEMI)'; the second term is a typo for NSTEMI and is narrated as NSTEMI.
export const script = {
  id: "ch1-04-mi-pci", index: 4, total: 18,
  title: "When was the last heart attack?",
  kicker: "CV history · MI & PCI", source: "Ch 1 · pp 2–3",
  poster: { at: "risk2", plus: 2.0 },
  sentences: [
    { id: "hook", text: "When was the last heart attack?" },
    { id: "doc", text: "For every previous infarction, / document the number, / the dates, / and the coronary anatomy." },
    { id: "chk", text: "Check the chart, / and look for Q waves / on the {EKG=E K G}." },
    { id: "risk1", text: "Surgical risk is higher / after a recent {STEMI=stemmy} / than after an {NSTEMI=en stemmy}." },
    { id: "risk2", text: "And it is highest early after the infarct, / falling after one week." },
    { id: "pci", text: "Now previous stents and angioplasty. / Note the left ventricular function / and coronary anatomy / from the angiography report." },
    { id: "pci2", text: "Record how many procedures, / when, / what type, / and the result." },
    { id: "fail", text: "Emergency surgery after a failed {PCI=P C I} / is high risk." },
    { id: "clop", text: "And after a recent {PCI=P C I}, / clopidogrel usually continues / for at least one month, / which can change how bypass is done." },
    { id: "rec", text: "Count, date, anatomy, timing. / Then the stent story." },
  ],
};
