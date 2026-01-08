export enum ViewState {
  CHAT = 'CHAT',
  PROTOCOLS = 'PROTOCOLS',
  PRODUCTS = 'PRODUCTS',
  SAFETY = 'SAFETY',
  LIVE_CONSULT = 'LIVE_CONSULT',
  DOCS = 'DOCS'
}

export interface Message {
  id: string;
  role: 'user' | 'model';
  text: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface ProtocolStep {
  title: string;
  description: string;
  details?: string[];
}

export interface Protocol {
  id: string;
  title: string;
  product: string;
  indication: string;
  steps: ProtocolStep[];
  contraindications: string[];
  dosing: string;
  vectors?: { name: string; description: string }[];
  imagePlaceholder?: string;
}

export interface Product {
  name: string;
  technology: string;
  indications: string[];
  composition: string;
  mechanism: string;
  benefits: string[];
  contraindications: string[];
  imageUrl?: string;
}