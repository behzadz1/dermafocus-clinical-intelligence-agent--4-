import { Protocol, Product } from '../types';



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
    imagePlaceholder: '/assets/protocol-placeholder-1.svg'
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
    imagePlaceholder: '/assets/protocol-placeholder-2.svg'
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
    imagePlaceholder: '/assets/protocol-placeholder-3.svg'
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
    imagePlaceholder: '/assets/protocol-placeholder-4.svg'
  }
];

export const PRODUCTS: Product[] = [
  // PN-HPT® Product Line (Polynucleotides)
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
  },
  // Purasomes Product Line (Exosomes & Secretomes)
  {
    name: 'Purasomes Skin Glow Complex',
    technology: 'AMPLEX Plus® (Exosomes)',
    composition: '20 billion exosomes + 20 growth factors from bovine colostrum + Vitamins + Minerals',
    indications: ['Skin rejuvenation', 'Dull skin', 'Uneven texture', 'Anti-aging'],
    mechanism: 'Exosomes enhance cell-to-cell communication, stimulating collagen synthesis and reducing trans-epidermal water loss.',
    benefits: [
      'Increased collagen synthesis',
      'Improved skin radiance',
      'Enhanced cellular regeneration',
      'Anti-inflammatory effect'
    ],
    contraindications: ['Bovine allergy', 'Active skin infection']
  },
  {
    name: 'Purasomes Nutri Complex 150+',
    technology: 'AMPLEX Plus® (Exosomes)',
    composition: '20 billion exosomes + 20 growth factors + Amino acids + DMAE-HA + Vitamins + Oligo-minerals',
    indications: ['Age spots', 'Oily skin', 'Dark spots', 'Post-blemish scarring'],
    mechanism: 'Comprehensive nutrient delivery via exosomes for skin regeneration and pigmentation regulation.',
    benefits: [
      'Regulates melanin production',
      'Reduces age spots',
      'Nourishes skin deeply',
      'Improves skin texture'
    ],
    contraindications: ['Bovine allergy']
  },
  {
    name: 'Purasomes Hair & Scalp Complex',
    technology: 'AMPLEX Plus® (Exosomes)',
    composition: '20 billion exosomes + 20 growth factors + Hair-specific nutrients',
    indications: ['Hair thinning', 'Scalp health', 'Hair follicle regeneration'],
    mechanism: 'Exosome-mediated delivery of growth factors directly to hair follicles for regeneration.',
    benefits: [
      'Stimulates hair follicle regeneration',
      'Improves scalp health',
      'Increases hair thickness',
      'Reduces hair shedding'
    ],
    contraindications: ['Bovine allergy', 'Scalp infections']
  },
  {
    name: 'Purasomes XCell',
    technology: 'AMPLEX Plus® (Exosomes)',
    composition: '20 billion exosomes + 20 growth factors + Advanced cellular matrix',
    indications: ['Advanced skin regeneration', 'Wound healing', 'Tissue repair'],
    mechanism: 'High-concentration exosome therapy for advanced cellular repair and tissue regeneration.',
    benefits: [
      'Accelerates wound healing',
      'Enhanced tissue repair',
      'Thicker dermal-epidermal junction',
      'Increased angiogenesis'
    ],
    contraindications: ['Bovine allergy', 'Active infection']
  }
];