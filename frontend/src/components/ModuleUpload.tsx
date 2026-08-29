import React, { useCallback, useState } from 'react';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { FiUploadCloud, FiX, FiCheckCircle, FiAlertCircle, FiInfo } from 'react-icons/fi';
import axios from 'axios';
import { AIProblemReview, ManualProblemFlagging } from './ProblemReview';
import './ModuleUpload.css';

interface IdentifiedProblem {
    problem: string;
    category: string;
    location: string;
    observation: string;
    condition: string;
    confidence: number;
    severity_estimate: string;
    student_impact: any;
    teacher_impact: any;
    evidence: string[];
    requires_inspection: boolean;
    scale_estimate?: string;
}

interface AnalysisResult {
    image_quality: any;
    image_category: string;
    problems: IdentifiedProblem[];
    limitations: string[];
}

interface UploadData {
    file: File;
    preview: string;
    description: string;
    progress: number;
    status: 'pending' | 'uploading' | 'success' | 'error';
    errorMessage?: string;
    analysis?: AnalysisResult;
}

interface ModuleUploadProps {
    activeSchoolId: string;
    moduleName: string;
}

export const ModuleUpload: React.FC<ModuleUploadProps> = ({ activeSchoolId, moduleName }) => {
    const [uploads, setUploads] = useState<UploadData[]>([]);

    const onDrop = useCallback((acceptedFiles: File[], fileRejections: FileRejection[]) => {
        const newUploads = acceptedFiles.map(file => ({
            file,
            preview: URL.createObjectURL(file),
            description: '',
            progress: 0,
            status: 'pending' as const
        }));

        const rejectedUploads = fileRejections.map(rejection => ({
            file: rejection.file,
            preview: '',
            description: '',
            progress: 0,
            status: 'error' as const,
            errorMessage: rejection.errors[0].message
        }));

        setUploads(prev => [...prev, ...newUploads, ...rejectedUploads]);
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
        onDrop,
        accept: {
            'image/jpeg': ['.jpeg', '.jpg'],
            'image/png': ['.png']
        },
        maxSize: 10 * 1024 * 1024
    });

    const removeUpload = (index: number) => {
        setUploads(prev => {
            const newUploads = [...prev];
            if (newUploads[index].preview) {
                 URL.revokeObjectURL(newUploads[index].preview);
            }
            newUploads.splice(index, 1);
            return newUploads;
        });
    };

    const handleFieldChange = (index: number, value: string) => {
        setUploads(prev => {
            const newUploads = [...prev];
            newUploads[index] = { ...newUploads[index], description: value };
            return newUploads;
        });
    };

    const submitUploads = async () => {
        for (let i = 0; i < uploads.length; i++) {
            if (uploads[i].status !== 'pending') continue;

            setUploads(prev => {
                const newUploads = [...prev];
                newUploads[i].status = 'uploading';
                return newUploads;
            });

            const formData = new FormData();
            formData.append('file', uploads[i].file);
            formData.append('school_id', activeSchoolId);
            formData.append('module', moduleName);
            // Defaulting category to module name for simplicity since they are 1:1 here
            formData.append('category', moduleName); 
            if (uploads[i].description) {
                formData.append('description', uploads[i].description);
            }

            try {
                const response = await axios.post('http://localhost:8000/api/v1/images/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                    onUploadProgress: (progressEvent) => {
                        const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
                        setUploads(prev => {
                            const newUploads = [...prev];
                            newUploads[i].progress = percentCompleted;
                            return newUploads;
                        });
                    }
                });

                setUploads(prev => {
                    const newUploads = [...prev];
                    newUploads[i].status = 'success';
                    newUploads[i].analysis = response.data.analysis;
                    return newUploads;
                });
            } catch (error: any) {
                setUploads(prev => {
                    const newUploads = [...prev];
                    newUploads[i].status = 'error';
                    newUploads[i].errorMessage = error.response?.data?.detail || 'Upload failed';
                    return newUploads;
                });
            }
        }
    };

    return (
        <div className="module-upload-container">
            <div {...getRootProps()} className={`module-dropzone ${isDragActive ? 'active' : ''}`}>
                <input {...getInputProps()} />
                <FiUploadCloud size={32} className="dropzone-icon" />
                {
                    isDragActive ?
                    <p>Drop to add to {moduleName}</p> :
                    <p>Upload to {moduleName} (JPG/PNG)</p>
                }
            </div>

            {uploads.length > 0 && (
                <div className="uploads-list module-uploads-list">
                    {uploads.map((upload, index) => (
                        <div key={index} className={`upload-item ${upload.status}`}>
                            <div className="upload-preview">
                                {upload.preview ? (
                                    <img src={upload.preview} alt="Preview" />
                                ) : (
                                    <div className="no-preview">No Preview</div>
                                )}
                            </div>
                            
                            <div className="upload-details">
                                <div className="upload-header">
                                    <span className="filename" title={upload.file.name}>{upload.file.name}</span>
                                    <button 
                                        className="remove-btn" 
                                        onClick={() => removeUpload(index)}
                                        disabled={upload.status === 'uploading'}
                                    >
                                        <FiX />
                                    </button>
                                </div>
                                
                                {upload.status === 'error' && (
                                    <div className="error-message">
                                        <FiAlertCircle /> {upload.errorMessage}
                                    </div>
                                )}

                                <div className="upload-fields">
                                    <input 
                                        type="text" 
                                        placeholder="Optional description..."
                                        value={upload.description}
                                        onChange={(e) => handleFieldChange(index, e.target.value)}
                                        disabled={upload.status !== 'pending' && upload.status !== 'error'}
                                    />
                                </div>
                                
                                {upload.status === 'uploading' && (
                                    <div className="progress-bar-container">
                                        <div className="progress-bar" style={{ width: `${upload.progress}%` }}></div>
                                    </div>
                                )}
                                
                                {upload.status === 'success' && (
                                    <div className="success-message">
                                        <FiCheckCircle /> Uploaded successfully
                                    </div>
                                )}

                                {/* AI Analysis Results Section */}
                                {upload.status === 'success' && upload.analysis && (
                                    <div className="analysis-results">
                                        <h4><FiInfo /> Analysis</h4>
                                        
                                        {!upload.analysis.image_quality.analysis_recommended ? (
                                             <div className="quality-rejection">
                                                 <strong>⚠️ Insufficient Quality: </strong> 
                                                 {upload.analysis.image_quality.reason}
                                             </div>
                                        ) : upload.analysis.problems.length === 0 ? (
                                            <p className="no-problems">No problems detected.</p>
                                        ) : (
                                            <ul className="problem-list">
                                                {upload.analysis.problems.map((prob, idx) => (
                                                    <li key={idx}>
                                                        <AIProblemReview 
                                                            problem={prob} 
                                                            schoolId={activeSchoolId} 
                                                        />
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                        
                                        <ManualProblemFlagging schoolId={activeSchoolId} imageId="temporary-frontend-id" imageUrl={upload.preview} />
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    
                    <button 
                        className="submit-btn" 
                        onClick={submitUploads}
                        disabled={!uploads.some(u => u.status === 'pending')}
                    >
                        Analyze Pending
                    </button>
                </div>
            )}
        </div>
    );
};
