export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: string;
  condition: string;
  avatar: string;
  lastVisit: string;
  nextAppointment: string;
  wearableData: {
    heartRate: number[];
    stepCount: number[];
  };
  sentiment: 'amazing' | 'good' | 'neutral' | 'poor' | 'terrible';
  privateNotes: string;
  researchTopic: string;
  researchContent: string[];
  doctorNotes: {
    id: string;
    date: string;
    time: string;
    content: string;
  }[];
}

export const patients: Patient[] = [
  {
    id: '1',
    name: 'Sarah Mitchell',
    age: 45,
    gender: 'Female',
    condition: 'Breast Cancer Stage II',
    avatar: 'SM',
    lastVisit: '2024-01-15',
    nextAppointment: '2024-02-01',
    wearableData: {
      heartRate: [72, 75, 68, 71, 74, 69, 73],
      stepCount: [4500, 5200, 3800, 4100, 4800, 5500, 4200],
    },
    sentiment: 'good',
    privateNotes: "Feeling more optimistic after last treatment. Energy levels improving. Family support has been incredible.",
    researchTopic: 'Breast Cancer Treatment Advances',
    researchContent: [
      "Recent clinical trials have shown promising results for HER2-positive breast cancer patients using targeted therapy combinations. The DESTINY-Breast03 trial demonstrated significant improvements in progression-free survival with trastuzumab deruxtecan compared to traditional treatments.",
      "Immunotherapy continues to show promise, particularly for triple-negative breast cancer. Pembrolizumab combined with chemotherapy has become a new standard of care for PD-L1 positive tumors, offering improved outcomes for patients who previously had limited options.",
      "Advances in genomic profiling now allow for more personalized treatment approaches. Tests like Oncotype DX help determine which patients will benefit most from chemotherapy, potentially sparing others from unnecessary side effects while maintaining excellent outcomes."
    ],
    doctorNotes: [
      { id: '1', date: '2024-01-15', time: '10:30 AM', content: 'Patient responding well to current treatment regimen. Tumor markers showing decrease. Recommend continuing current protocol.' },
      { id: '2', date: '2024-01-02', time: '2:15 PM', content: 'Reviewed imaging results. No new metastases detected. Patient reports mild fatigue but manageable.' },
    ]
  },
  {
    id: '2',
    name: 'James Anderson',
    age: 62,
    gender: 'Male',
    condition: 'Type 2 Diabetes',
    avatar: 'JA',
    lastVisit: '2024-01-18',
    nextAppointment: '2024-02-15',
    wearableData: {
      heartRate: [78, 82, 76, 80, 79, 77, 81],
      stepCount: [3200, 2800, 3500, 2900, 3100, 3400, 2700],
    },
    sentiment: 'neutral',
    privateNotes: "Struggling with diet changes. Miss my usual foods. Trying to stay positive but it's hard.",
    researchTopic: 'Diabetes Management Innovations',
    researchContent: [
      "GLP-1 receptor agonists like semaglutide have revolutionized type 2 diabetes management. Beyond glucose control, these medications offer significant cardiovascular benefits and weight reduction, addressing multiple aspects of metabolic syndrome simultaneously.",
      "Continuous glucose monitoring (CGM) technology has transformed patient self-management. Real-time data allows for immediate dietary and activity adjustments, leading to improved HbA1c levels and reduced hypoglycemic events.",
      "Recent research emphasizes the importance of personalized nutrition in diabetes management. Gut microbiome analysis can help predict individual glycemic responses to foods, enabling more effective dietary recommendations."
    ],
    doctorNotes: [
      { id: '1', date: '2024-01-18', time: '9:00 AM', content: 'HbA1c improved to 7.2%. Discussed importance of consistent medication adherence. Referred to dietitian for meal planning support.' },
    ]
  },
  {
    id: '3',
    name: 'Emily Chen',
    age: 34,
    gender: 'Female',
    condition: 'Anxiety Disorder',
    avatar: 'EC',
    lastVisit: '2024-01-20',
    nextAppointment: '2024-01-27',
    wearableData: {
      heartRate: [85, 92, 78, 88, 82, 90, 86],
      stepCount: [6200, 7500, 5800, 8100, 6900, 7200, 6500],
    },
    sentiment: 'poor',
    privateNotes: "Work stress overwhelming. Sleep has been terrible. Panic attacks returning. Feel like I'm failing at everything.",
    researchTopic: 'Anxiety Treatment Approaches',
    researchContent: [
      "Cognitive Behavioral Therapy (CBT) remains the gold standard for anxiety disorders, with digital CBT platforms showing comparable efficacy to in-person therapy. These accessible options can bridge treatment gaps and provide immediate support.",
      "Emerging research on the gut-brain axis reveals promising connections between microbiome health and anxiety symptoms. Probiotic supplementation and dietary interventions may serve as valuable adjuncts to traditional treatments.",
      "Heart rate variability biofeedback training has demonstrated effectiveness in reducing anxiety symptoms. By teaching patients to regulate their autonomic nervous system, this technique provides lasting self-management skills."
    ],
    doctorNotes: [
      { id: '1', date: '2024-01-20', time: '3:45 PM', content: 'Increased anxiety symptoms noted. Adjusted medication dosage. Strongly recommended resuming weekly therapy sessions. Follow-up in one week.' },
      { id: '2', date: '2024-01-06', time: '11:00 AM', content: 'Patient stable on current regimen. Practicing breathing exercises regularly. Continue monitoring.' },
    ]
  },
  {
    id: '4',
    name: 'Robert Williams',
    age: 55,
    gender: 'Male',
    condition: 'Hypertension',
    avatar: 'RW',
    lastVisit: '2024-01-12',
    nextAppointment: '2024-02-12',
    wearableData: {
      heartRate: [68, 70, 66, 72, 69, 71, 67],
      stepCount: [8500, 9200, 7800, 8900, 9500, 8100, 8700],
    },
    sentiment: 'amazing',
    privateNotes: "Feeling the best I have in years! Walking every day, blood pressure under control. Life is good!",
    researchTopic: 'Hypertension Control Strategies',
    researchContent: [
      "The SPRINT trial established that intensive blood pressure control (systolic <120 mmHg) significantly reduces cardiovascular events compared to standard targets. This has reshaped treatment guidelines for many patient populations.",
      "Renal denervation has re-emerged as a promising intervention for resistant hypertension. Second-generation devices show consistent blood pressure reductions, offering hope for patients unresponsive to medication.",
      "Lifestyle modifications including the DASH diet, regular aerobic exercise, and stress reduction techniques can reduce systolic blood pressure by 10-15 mmHg, sometimes matching or exceeding medication effects."
    ],
    doctorNotes: [
      { id: '1', date: '2024-01-12', time: '1:30 PM', content: 'Excellent progress! BP consistently at target. Patient highly motivated with exercise regimen. Reduced medication dosage as reward for lifestyle changes.' },
    ]
  },
];
