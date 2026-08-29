import mongoose from 'mongoose';

const ImageSchema = new mongoose.Schema({
  school_id: { type: String, required: true, index: true },
  category: { type: String, required: true },
  description: { type: String },
  original_filename: { type: String, required: true },
  storage_reference: { type: String, required: true },
  analysis_status: { 
    type: String, 
    enum: ['pending', 'analyzing', 'completed', 'failed'],
    default: 'pending' 
  },
  upload_timestamp: { type: Date, default: Date.now }
});

const StudentImpactSchema = new mongoose.Schema({
  level: { type: String, enum: ['High', 'Medium', 'Low', 'Unknown'] },
  areas: [{ type: String }],
  reasoning: { type: String }
});

const TeacherImpactSchema = new mongoose.Schema({
  level: { type: String, enum: ['High', 'Medium', 'Low', 'Unknown'] },
  areas: [{ type: String }],
  reasoning: { type: String }
});

const ProblemSchema = new mongoose.Schema({
  school_id: { type: String, required: true, index: true },
  image_id: { type: mongoose.Schema.Types.ObjectId, ref: 'Image', required: true },
  
  // Source tracking
  source: { type: String, enum: ['AI', 'ADMINISTRATOR', 'ENGINEER'], required: true },
  original_ai_problem_id: { type: mongoose.Schema.Types.ObjectId, ref: 'Problem' }, // Populated if a human edited an AI finding
  
  // Core Problem Info
  title: { type: String, required: true },
  category: { type: String, required: true },
  observation: { type: String, required: true }, // The actual description
  evidence: [{ type: String }], // Array of visual evidence sentences
  location_in_school: { type: String },
  location_in_image: { // E.g., x, y coordinates or "top right" - mostly for manual flagging
    x: Number,
    y: Number,
    description: String
  },

  // Assessments
  condition: { type: String, enum: ['Good', 'Fair', 'Poor', 'Critical', 'Unknown'] },
  student_impact: StudentImpactSchema,
  teacher_impact: TeacherImpactSchema,
  scale_estimate: { type: String }, // "Approximately 4 damaged desks"
  
  // Confidence and Flags
  ai_confidence: { type: Number, min: 0, max: 1 },
  requires_inspection: { type: Boolean, default: false },
  inspection_reason: { type: String },
  
  // Human overrides / priorities
  human_priority: { type: String, enum: ['Critical', 'High', 'Medium', 'Low', 'Vulnerable', 'Needs attention', null], default: null },
  human_notes: { type: String },

  // System Tracking
  status: { type: String, enum: ['Active', 'Resolved', 'Rejected'], default: 'Active' },
}, { timestamps: true });

export const Image = mongoose.model('Image', ImageSchema);
export const Problem = mongoose.model('Problem', ProblemSchema);
