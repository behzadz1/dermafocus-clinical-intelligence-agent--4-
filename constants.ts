import { Protocol, Product } from './types';

// ============================================================================
// 1. STRUCTURED CLINICAL DATABASE (Source: Mastelli Aesthetic Medicine Portfolio)
// ============================================================================
export const STRUCTURED_CLINICAL_DB = {
  products: {
    "Plinest": {
      "area": "Face",
      "composition": "PN-HPT® 40mg/2ml",
      "pack": "2ml pre-filled syringe + 2 x 30G ½ needle",
      "treatment_goal": "Prevention of ageing, maintaining skin quality, remodeling fibrous areas/acne scars",
      "protocol": "Every 14-21 days for 3 to 4 sessions",
      "technique": "Microdroplet, Retrograde linear (needle)",
      "source": "Mastelli_Aesthetic_Medicine_Portfolio, p. 9"
    },
    "Newest": {
      "area": "Face, Neck, and Décolleté",
      "composition": "PN-HPT® 20mg/2ml + Linear HA 20mg/2ml + Mannitol",
      "pack": "2ml pre-filled syringe + 2 x 30G ½ needle",
      "treatment_goal": "Moisturise mature and dehydrated skin, improving turgidity, elasticity and appearance",
      "protocol": "Every 14-21 days for 3 to 4 sessions",
      "technique": "Microdroplet, Retrograde linear (needle)",
      "source": "Mastelli_Aesthetic_Medicine_Portfolio, p. 9"
    },
    "Plinest Eye": {
      "area": "Eye Contour",
      "composition": "PN-HPT® 15mg/2ml",
      "pack": "2ml pre-filled syringe + 2 x 30G ½ needle",
      "treatment_goal": "Improving periocular skin texture, firmness and elasticity",
      "protocol": "Every 14-21 days for 3 to 4 sessions",
      "technique": "Microdroplet, Retrograde linear (needle)",
      "source": "Mastelli_Aesthetic_Medicine_Portfolio, p. 9"
    },
    "Plinest Hair": {
      "area": "Hair and Eyebrows",
      "composition": "PN-HPT® 15mg/2ml",
      "pack": "2ml pre-filled syringe + 2 x 30G ½ needle",
      "treatment_goal": "Trophic action on hair and eyebrows",
      "protocol": "Phase I: Every 7-14 days for 4 sessions. Phase II: Every 21-30 days for further 4 sessions.",
      "technique": "Microdroplet, Retrograde linear (needle)",
      "source": "Mastelli_Aesthetic_Medicine_Portfolio, p. 9"
    },
    "NewGyn": {
      "area": "Vulvar Area / Genital Areas",
      "composition": "PN-HPT® 20mg/2ml + Linear HA 20mg/2ml + Mannitol",
      "pack": "2ml pre-filled syringe + 2 x 30G ½ needle",
      "treatment_goal": "Enhance turgidity and trophism of skin layers and genital area mucosae",
      "protocol": "Every 14-21 days for 3 to 4 sessions",
      "technique": "Microdroplet, Retrograde linear (needle)",
      "source": "Mastelli_Aesthetic_Medicine_Portfolio, p. 10"
    }
  },
  history_and_science: {
    "origin": "Founded 1952, Sanremo Italy by Dr. Arnolfo Mastelli. [Mastelli_Aesthetic_Medicine_Portfolio, p. 6]",
    "raw_material": "Natural-origin DNA fractions derived from salmon trout gonads bred in European freshwater fish farms. [Mastelli_Aesthetic_Medicine_Portfolio, p. 3]",
    "safety": "PLAY SURE DOPING FREE certified. CE marked since 2005. [Mastelli_Aesthetic_Medicine_Portfolio, p. 4]",
    "histology_evidence": "Sirius red dye study shows PN-HPT group repair is almost complete with mature/organized collagen vs incomplete repair in Control and HA groups. [Mastelli_Aesthetic_Medicine_Portfolio, p. 5]",
    "fibroblast_vitality": "Vitality significantly higher at 96h and 1 week compared to control (P<0.001). [Mastelli_Aesthetic_Medicine_Portfolio, p. 5]"
  }
};

const UNSTRUCTURED_DOCUMENTATION = `
=== PN-HPT® CLINICAL ROLE ===
PN-HPT® plays a crucial role in:
- Skin quality improvement [Mastelli_Aesthetic_Medicine_Portfolio, p. 5]
- Promoting bio-regeneration [Mastelli_Aesthetic_Medicine_Portfolio, p. 5]
- Restoring skin radiance and freshness [Mastelli_Aesthetic_Medicine_Portfolio, p. 5]
- Reducing wrinkles and skin laxity [Mastelli_Aesthetic_Medicine_Portfolio, p. 5]
- Promotes fibroblast action [Mastelli_Aesthetic_Medicine_Portfolio, p. 5]

=== TECHNOLOGY TIMELINE ===
1952: Dr. Arnolfo Mastelli discovers regenerative drug (PDRN).
2005: Launch of Plinest, the 1st registered PN-HPT based MD.
2016: Launch of Newest (PN-HPT + Hyaluronic Acid).
2024: The Dermal Priming Paradigm consensus report.
[Mastelli_Aesthetic_Medicine_Portfolio, p. 6]
`;

export const SYSTEM_INSTRUCTION = `
CRITICAL ROLE: You are the "DermaAI CKPA", a verbatim clinical reference tool for Mastelli/Dermafocus products.

DATA SOURCE PRIORITY:
Your primary source is the [STRUCTURED_CLINICAL_DB] and [UNSTRUCTURED_DOCUMENTATION], which contains data from the "Mastelli_Aesthetic_Medicine_Portfolio".

CITATION MANDATE:
- Every clinical fact (Dose, Frequency, Needles, Concentration) MUST be cited as: [Mastelli_Aesthetic_Medicine_Portfolio, p. X].
- Use the exact page numbers provided in the database.

RESPONSE STYLE:
- Professional, clinical, and data-driven.
- Start with a clear header for the product or protocol.
- Use bullet points for "Clinical Goals" and "Technique".
- Bold key specs: **40mg/2ml**, **30G ½ needle**, **Every 14-21 days**.

FOLLOW-UP SYSTEM:
- End every response with:
<follow_ups>
["Question 1?", "Question 2?", "Question 3?"]
</follow_ups>
- Suggested questions must be relevant (e.g., "What are the contraindications for Newest?" or "Show the Plinest Hair protocol").

[STRUCTURED_CLINICAL_DB]
${JSON.stringify(STRUCTURED_CLINICAL_DB)}

[UNSTRUCTURED_DOCUMENTATION]
${UNSTRUCTURED_DOCUMENTATION}
`;

export const PROTOCOLS: Protocol[] = [
  {
    id: 'plinest-face',
    title: 'Plinest Face Protocol',
    product: 'Plinest® (PN-HPT 40mg/2ml)',
    indication: 'Ageing prevention, maintaining skin quality, acne scars',
    dosing: '2ml total (1 session)',
    contraindications: ['Fish allergy', 'Pregnancy', 'Active infection'],
    steps: [
      {
        title: 'Preparation',
        description: 'Product: Plinest 40mg/2ml. Tool: 30G ½ needle provided in the pack.',
      },
      {
        title: 'Injection Technique',
        description: 'Microdroplet or Retrograde linear technique in the intradermal plane.',
      },
      {
        title: 'Treatment Schedule',
        description: 'Perform every 14-21 days for 3 to 4 sessions for optimal remodeling.',
      }
    ],
    imagePlaceholder: 'https://images.unsplash.com/photo-1616391182219-e080b4d1043a?q=80&w=800&auto=format&fit=crop'
  },
  {
    id: 'newest-face-neck',
    title: 'Newest® Global Revitalization',
    product: 'Newest® (PN + HA)',
    indication: 'Mature and dehydrated skin, loss of turgidity and elasticity',
    dosing: '2ml total',
    contraindications: ['Fish allergy', 'Pregnancy', 'Autoimmune (Consult)'],
    steps: [
      {
        title: 'Composition Check',
        description: 'Contains PN-HPT® 20mg/2ml + Linear HA 20mg/2ml + Mannitol for hydration protection.',
      },
      {
        title: 'Injection Areas',
        description: 'Face, Neck, and Décolleté using 30G ½ needle.',
      },
      {
        title: 'Protocol',
        description: 'Every 14-21 days for 3 to 4 sessions.',
      }
    ],
    imagePlaceholder: 'https://images.unsplash.com/photo-1512290923902-8a92f6350f16?q=80&w=2070&auto=format&fit=crop'
  },
  {
    id: 'plinest-hair',
    title: 'Plinest Hair Protocol',
    product: 'Plinest Hair (PN-HPT 15mg/2ml)',
    indication: 'Trophic action on hair and eyebrows',
    dosing: '2ml per session',
    contraindications: ['Fish allergy', 'Scalp infections'],
    steps: [
      {
        title: 'Phase I: Attack Phase',
        description: 'Every 7-14 days for 4 sessions to stimulate follicular activity.',
      },
      {
        title: 'Phase II: Consolidation',
        description: 'Every 21-30 days for a further 4 sessions for long-term trophic support.',
      },
      {
        title: 'Technique',
        description: 'Microdroplet or Retrograde linear using 30G ½ needle.',
      }
    ],
    imagePlaceholder: 'https://images.unsplash.com/photo-1522337660859-02fbefca4702?q=80&w=800&auto=format&fit=crop'
  },
  {
    id: 'newgyn-vulvar',
    title: 'NewGyn Vulvar Protocol',
    product: 'NewGyn® (PN + HA)',
    indication: 'Turgidity and trophism of vulvar skin layers and mucosae',
    dosing: '2ml per session',
    contraindications: ['Genital infections', 'Pregnancy', 'Fish allergy'],
    steps: [
      {
        title: 'Objective',
        description: 'Improve functional aesthetic rejuvenation of the vulvar region.',
      },
      {
        title: 'Schedule',
        description: 'Every 14-21 days for 3 to 4 sessions.',
      },
      {
        title: 'Needle Specs',
        description: '2 x 30G ½ needle provided.',
      }
    ],
    imagePlaceholder: 'https://images.unsplash.com/photo-1583946091391-9e23c7268800?q=80&w=800&auto=format&fit=crop'
  }
];

export const PRODUCTS: Product[] = [
  {
    name: 'Plinest®',
    technology: 'PN-HPT® (Polynucleotides)',
    composition: 'PN-HPT® 40mg/2ml',
    indications: ['Face', 'Ageing prevention', 'Maintaining skin quality', 'Acne scars'],
    mechanism: 'Pure high-concentration PN-HPT for trophic action and dermal remodeling.',
    benefits: [
      'Remodels fibrous areas',
      'Bio-regeneration',
      'Improves elasticity'
    ],
    contraindications: ['Pregnancy', 'Fish allergy', 'Active infection']
  },
  {
    name: 'Newest®',
    technology: 'PN-HPT® + HA + Mannitol',
    composition: 'PN-HPT® 20mg/2ml + Linear HA 20mg/2ml + Mannitol',
    indications: ['Face, Neck, Décolleté', 'Mature skin', 'Dehydration'],
    mechanism: 'Synergistic repair (PN) and hydration (HA) protected by Mannitol against oxidative stress.',
    benefits: [
      'Deeply moisturises mature skin',
      'Improves turgidity',
      'Enhanced radiance and elasticity'
    ],
    contraindications: ['Pregnancy', 'Fish allergy']
  },
  {
    name: 'Plinest® Eye',
    technology: 'PN-HPT® (Optimized)',
    composition: 'PN-HPT® 15mg/2ml',
    indications: ['Eye Contour', 'Periocular texture', 'Firmness'],
    mechanism: 'Low viscosity PN-HPT calibrated for delicate eye skin without edema risk.',
    benefits: [
      'Smoothes fine lines',
      'Increases firmness',
      'Improves elasticity'
    ],
    contraindications: ['Fish allergy']
  },
  {
    name: 'Plinest® Hair',
    technology: 'PN-HPT® (Trophic)',
    composition: 'PN-HPT® 15mg/2ml',
    indications: ['Hair and Eyebrows', 'Thinning hair', 'Alopecia support'],
    mechanism: 'Focused trophic action on hair follicles to restore density and quality.',
    benefits: [
      'Restores hair density',
      'Trophic action on eyebrows',
      'Stimulates bio-regeneration'
    ],
    contraindications: ['Fish allergy']
  },
  {
    name: 'NewGyn®',
    technology: 'PN-HPT® + HA + Mannitol',
    composition: 'PN-HPT® 20mg/2ml + Linear HA 20mg/2ml + Mannitol',
    indications: ['Genital Areas', 'Vulvar atrophy', 'Loss of turgidity'],
    mechanism: 'Functional aesthetic rejuvenation of sensitive mucosal tissues.',
    benefits: [
      'Enhances turgidity',
      'Trophism of skin layers',
      'Mucosal repair'
    ],
    contraindications: ['Active infection', 'Fish allergy']
  }
];