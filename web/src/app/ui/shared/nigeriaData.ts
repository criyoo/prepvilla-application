export const NIGERIA_STATE_CITIES: Record<string, string[]> = {
  Abia: ["Aba", "Arochukwu", "Bende", "Ohafia", "Umuahia", "Uzuakoli"],
  Adamawa: ["Ganye", "Jimeta", "Mubi", "Numan", "Yola"],
  "Akwa Ibom": ["Abak", "Eket", "Ikot Ekpene", "Oron", "Uyo"],
  Anambra: ["Awka", "Ekwulobia", "Ihiala", "Nnewi", "Onitsha"],
  Bauchi: ["Azare", "Bauchi", "Jama'are", "Katagum", "Misau"],
  Bayelsa: ["Brass", "Kaiama", "Ogbia", "Sagbama", "Yenagoa"],
  Benue: ["Gboko", "Katsina-Ala", "Makurdi", "Otukpo", "Vandeikya"],
  Borno: ["Bama", "Biu", "Dikwa", "Gwoza", "Maiduguri"],
  "Cross River": ["Calabar", "Ikom", "Obudu", "Ogoja", "Ugep"],
  Delta: ["Agbor", "Asaba", "Effurun", "Ozoro", "Sapele", "Ughelli", "Warri"],
  Ebonyi: ["Abakaliki", "Afikpo", "Ezza", "Ikwo", "Onueke"],
  Edo: ["Auchi", "Benin City", "Ekpoma", "Irrua", "Uromi"],
  Ekiti: ["Ado Ekiti", "Ijero Ekiti", "Ikere Ekiti", "Ikole Ekiti", "Oye Ekiti"],
  Enugu: ["Agbani", "Enugu", "Nsukka", "Oji River", "Udi"],
  "Federal Capital Territory": ["Abaji", "Abuja", "Bwari", "Dutse", "Gwagwalada", "Kuje", "Kubwa", "Nyanya"],
  Gombe: ["Bajoga", "Billiri", "Dukku", "Gombe", "Kaltungo"],
  Imo: ["Mbaise", "Oguta", "Okigwe", "Orlu", "Owerri"],
  Jigawa: ["Birnin Kudu", "Dutse", "Gumel", "Hadejia", "Kazaure"],
  Kaduna: ["Kachia", "Kaduna", "Kafanchan", "Sabon Gari", "Zaria"],
  Kano: ["Bichi", "Gaya", "Kano", "Rano", "Wudil"],
  Katsina: ["Daura", "Dutsin-Ma", "Funtua", "Katsina", "Malumfashi"],
  Kebbi: ["Argungu", "Birnin Kebbi", "Jega", "Yauri", "Zuru"],
  Kogi: ["Anyigba", "Idah", "Kabba", "Lokoja", "Okene"],
  Kwara: ["Ilorin", "Jebba", "Lafiagi", "Offa", "Omu-Aran"],
  Lagos: ["Ajah", "Badagry", "Epe", "Ikeja", "Ikorodu", "Lagos", "Lekki", "Surulere"],
  Nasarawa: ["Akwanga", "Karu", "Keffi", "Keana", "Lafia", "Nasarawa"],
  Niger: ["Bida", "Kontagora", "Minna", "New Bussa", "Suleja"],
  Ogun: ["Abeokuta", "Ijebu Igbo", "Ijebu Ode", "Ilaro", "Ota", "Sagamu"],
  Ondo: ["Akure", "Igbokoda", "Ikare", "Okitipupa", "Ondo", "Owo"],
  Osun: ["Ede", "Ejigbo", "Ikirun", "Ilesa", "Ile-Ife", "Osogbo"],
  Oyo: ["Eruwa", "Ibadan", "Iseyin", "Ogbomoso", "Oyo", "Saki"],
  Plateau: ["Bukuru", "Jos", "Langtang", "Pankshin", "Shendam"],
  Rivers: ["Bonny", "Degema", "Eleme", "Omoku", "Port Harcourt"],
  Sokoto: ["Gwadabawa", "Illela", "Sokoto", "Tambuwal", "Wurno"],
  Taraba: ["Bali", "Gembu", "Jalingo", "Takum", "Wukari"],
  Yobe: ["Damaturu", "Gashua", "Geidam", "Nguru", "Potiskum"],
  Zamfara: ["Anka", "Gusau", "Kaura Namoda", "Shinkafi", "Talata Mafara"],
};

export const NIGERIA_STATES = Object.keys(NIGERIA_STATE_CITIES);

export const NIGERIAN_SCHOOL_SUBJECTS = [
  "Agricultural Science",
  "Animal Husbandry",
  "Arabic",
  "Basic Science",
  "Basic Technology",
  "Biology",
  "Book Keeping",
  "Business Studies",
  "Catering Craft Practice",
  "Chemistry",
  "Christian Religious Studies",
  "Civic Education",
  "Commerce",
  "Computer Studies",
  "Cultural and Creative Arts",
  "Data Processing",
  "Economics",
  "English Language",
  "Financial Accounting",
  "Fine Art",
  "Food and Nutrition",
  "French",
  "Further Mathematics",
  "Geography",
  "Government",
  "Hausa",
  "History",
  "Home Economics",
  "Igbo",
  "Insurance",
  "Islamic Studies",
  "Literature in English",
  "Marketing",
  "Mathematics",
  "Metalwork",
  "Music",
  "Office Practice",
  "Physical and Health Education",
  "Physics",
  "Printing Craft Practice",
  "Store Management",
  "Technical Drawing",
  "Textile Trade",
  "Tourism",
  "Visual Arts",
  "Woodwork",
  "Yoruba",
];

export type SubjectCategory = {
  key: string;
  label: string;
  description: string;
  subjects: string[];
};

export const SUBJECT_CATEGORIES: SubjectCategory[] = [
  {
    key: "mathematics",
    label: "Mathematics",
    description: "Core maths, numeracy, and advanced quantitative subjects.",
    subjects: [
      "Mathematics",
      "Further Mathematics",
      "Basic Mathematics",
      "General Mathematics",
      "Statistics",
      "Quantitative Reasoning",
      "Mental Maths",
    ],
  },
  {
    key: "english",
    label: "English",
    description: "English language, literacy, reading, writing, and communication.",
    subjects: [
      "English",
      "English Language",
      "Literature in English",
      "Grammar",
      "Phonics",
      "Reading",
      "Reading Comprehension",
      "Creative Writing",
      "Diction",
      "Public Speaking",
    ],
  },
  {
    key: "sciences",
    label: "Sciences",
    description: "General science, laboratory subjects, and health-related studies.",
    subjects: [
      "Basic Science",
      "Biology",
      "Chemistry",
      "Physics",
      "Agricultural Science",
      "Animal Husbandry",
      "Food and Nutrition",
      "Environmental Science",
      "Physical and Health Education",
      "Health Science",
    ],
  },
  {
    key: "programming",
    label: "Programming",
    description: "Programming languages, software development, and computer studies.",
    subjects: [
      "Programming",
      "Python",
      "Java",
      "JavaScript",
      "TypeScript",
      "Golang",
      "Rust",
      "Ruby",
      "PHP",
      "C",
      "C++",
      "C#",
      "Swift",
      "Kotlin",
      "SQL",
      "Web Development",
      "Mobile App Development",
      "Software Engineering",
      "Backend Development",
      "Frontend Development",
    ],
  },
  {
    key: "humanities",
    label: "Humanities",
    description: "Social sciences, civic studies, religion, and history.",
    subjects: [
      "Civic Education",
      "Christian Religious Studies",
      "Islamic Studies",
      "Geography",
      "Government",
      "History",
      "Economics",
      "Commerce",
      "Social Studies",
      "Philosophy",
    ],
  },
  {
    key: "business & finance",
    label: "Business & Finance",
    description: "Business studies, accounting, marketing, and commercial subjects.",
    subjects: [
      "Book Keeping",
      "Business Studies",
      "Commerce",
      "Economics",
      "Financial Accounting",
      "Insurance",
      "Marketing",
      "Office Practice",
      "Store Management",
      "Entrepreneurship",
      "Finance",
    ],
  },
  {
    key: "technology",
    label: "Technology",
    description: "Digital literacy, applied technology, and technical tool subjects.",
    subjects: [
      "Basic Technology",
      "Computer Studies",
      "Data Processing",
      "Technical Drawing",
      "Robotics",
      "Graphic Design",
      "UI/UX Design",
      "Product Design",
      "Digital Literacy",
    ],
  },
  {
    key: "vocational",
    label: "Vocational",
    description: "Practical trade, home, craft, and employability subjects.",
    subjects: [
      "Catering Craft Practice",
      "Home Economics",
      "Metalwork",
      "Printing Craft Practice",
      "Textile Trade",
      "Tourism",
      "Woodwork",
      "Food and Nutrition",
      "Fashion Design",
      "Cosmetology",
    ],
  },
  {
    key: "arts & creative",
    label: "Arts & Creative",
    description: "Visual, performing, and expressive creative subjects.",
    subjects: [
      "Cultural and Creative Arts",
      "Fine Art",
      "Music",
      "Visual Arts",
      "Creative Writing",
      "Drama",
      "Photography",
      "Drawing",
    ],
  },
  {
    key: "languages",
    label: "Languages",
    description: "Local and international spoken languages.",
    subjects: [
      "Arabic",
      "French",
      "German",
      "Spanish",
      "Mandarin Chinese",
      "Portuguese",
      "Italian",
      "Hausa",
      "Igbo",
      "Yoruba",
      "English Speaking",
      "Conversational English",
    ],
  },
  {
    key: "exam-prep",
    label: "Exam Prep",
    description: "Standardized test preparation and school entrance coaching.",
    subjects: [
      "IELTS",
      "TOEFL",
      "SAT",
      "GRE",
      "GMAT",
      "WAEC",
      "NECO",
      "JAMB",
      "Common Entrance",
    ],
  },
];

export const FEATURED_SUBJECT_CATEGORY_KEYS = [
  "mathematics",
  "english",
  "sciences",
  "programming",
  "humanities",
  "business & finance",
  "technology",
  "vocational",
  "arts & creative",
  "languages",
  "exam-prep",
] as const;

export function normalizeSubjectCategoryKey(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

const SUBJECT_CATEGORY_BY_KEY = new Map(
  SUBJECT_CATEGORIES.flatMap((category) => [
    [normalizeSubjectCategoryKey(category.key), category] as const,
    [normalizeSubjectCategoryKey(category.label), category] as const,
  ]),
);

export function normalizeSubjectTerm(value: string) {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

export function subjectTermsMatch(left: string, right: string) {
  const normalizedLeft = normalizeSubjectTerm(left);
  const normalizedRight = normalizeSubjectTerm(right);
  if (!normalizedLeft || !normalizedRight) return false;
  if (normalizedLeft.length <= 2 || normalizedRight.length <= 2) {
    return normalizedLeft === normalizedRight;
  }
  return (
    normalizedLeft === normalizedRight ||
    normalizedLeft.includes(normalizedRight) ||
    normalizedRight.includes(normalizedLeft)
  );
}

export function findSubjectCategoryByKey(value: string) {
  return SUBJECT_CATEGORY_BY_KEY.get(normalizeSubjectCategoryKey(value)) ?? null;
}

export function findSubjectCategoryByLabel(value: string) {
  return SUBJECT_CATEGORIES.find((category) => subjectTermsMatch(category.label, value)) ?? null;
}

export function findSubjectCategoryBySubject(value: string) {
  return (
    SUBJECT_CATEGORIES.find((category) =>
      category.subjects.some((subject) => subjectTermsMatch(subject, value)),
    ) ?? null
  );
}

export function getSubjectsForCategory(categoryKey: string) {
  return findSubjectCategoryByKey(categoryKey)?.subjects ?? [];
}

export const ALL_TUTOR_SUBJECT_OPTIONS = Array.from(
  new Set([
    ...NIGERIAN_SCHOOL_SUBJECTS,
    ...SUBJECT_CATEGORIES.flatMap((category) => category.subjects),
    "English",
  ]),
);

export const NIGERIAN_TERTIARY_QUALIFICATIONS = [
  "National Certificate in Education (NCE)",
  "National Diploma (ND)",
  "Higher National Diploma (HND)",
  "Bachelor of Arts (B.A.)",
  "Bachelor of Agriculture (B.Agric.)",
  "Bachelor of Education (B.Ed.)",
  "Bachelor of Engineering (B.Eng.)",
  "Bachelor of Laws (LL.B.)",
  "Bachelor of Medical Laboratory Science (B.MLS)",
  "Bachelor of Medicine, Bachelor of Surgery (MBBS)",
  "Bachelor of Nursing Science (B.NSc.)",
  "Bachelor of Pharmacy (B.Pharm.)",
  "Bachelor of Science (B.Sc.)",
  "Bachelor of Technology (B.Tech.)",
  "Doctor of Philosophy (Ph.D.)",
  "Master of Arts (M.A.)",
  "Master of Business Administration (MBA)",
  "Master of Education (M.Ed.)",
  "Master of Philosophy (M.Phil.)",
  "Master of Science (M.Sc.)",
  "Postgraduate Diploma (PGD)",
  "Postgraduate Diploma in Education (PGDE)",
  "Professional Diploma",
];

export const WORLD_LANGUAGES = [
  "Arabic",
  "Bengali",
  "Dutch",
  "English",
  "French",
  "Gujarati",
  "German",
  "Hausa",
  "Hindi",
  "Igbo",
  "Indonesian",
  "Italian",
  "Japanese",
  "Korean",
  "Mandarin Chinese",
  "Marathi",
  "Persian",
  "Polish",
  "Portuguese",
  "Punjabi",
  "Russian",
  "Spanish",
  "Swahili",
  "Tamil",
  "Telugu",
  "Thai",
  "Turkish",
  "Ukrainian",
  "Urdu",
  "Vietnamese",
  "Yoruba",
];
