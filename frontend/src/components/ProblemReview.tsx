import React, { useState } from 'react';
import axios from 'axios';
import { FiEdit, FiCheck, FiX, FiFlag, FiSave } from 'react-icons/fi';
import './ProblemReview.css';

interface ProblemReviewProps {
    problem: any; // We'll keep typing loose here for speed, but mapped to our IdentifiedProblem
    problemId?: string; // If it's already in the DB
    schoolId: string;
    imageId?: string;
}

export const AIProblemReview: React.FC<ProblemReviewProps> = ({ problem, problemId }) => {
    const [status, setStatus] = useState<string>('Pending Review');
    const [notes, setNotes] = useState<string>('');
    const [priority, setPriority] = useState<string>('');
    const [isEditing, setIsEditing] = useState(false);
    
    // Editable fields
    const [title, setTitle] = useState(problem.problem);
    const [condition, setCondition] = useState(problem.condition);
    const [description, setDescription] = useState(problem.observation);

    const handleSaveReview = async (newStatus: string) => {
        // In a real app, problemId would be passed down from the newly created records
        if (!problemId) return; 

        try {
            await axios.put(`http://localhost:8000/api/v1/problems/${problemId}/review`, {
                human_status: newStatus,
                human_priority: priority,
                human_notes: notes,
                title: title !== problem.problem ? title : undefined,
                condition: condition !== problem.condition ? condition : undefined,
                description: description !== problem.observation ? description : undefined
            });
            setStatus(newStatus);
            setIsEditing(false);
        } catch (error) {
            console.error("Failed to save review", error);
            alert("Failed to save review");
        }
    };

    return (
        <div className={`problem-card review-status-${status.toLowerCase().replace(' ', '-')}`}>
            <div className="problem-header">
                {isEditing ? (
                    <input 
                        className="edit-title-input" 
                        value={title} 
                        onChange={e => setTitle(e.target.value)} 
                    />
                ) : (
                    <span className="problem-issue">{title}</span>
                )}
                
                <span className="source-badge ai-source">Source: AI</span>
            </div>

            <div className="observation">
                <strong>Observation:</strong> 
                {isEditing ? (
                    <textarea 
                        className="edit-desc-input"
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        style={{width: '100%', minHeight: '60px', marginTop: '5px'}}
                    />
                ) : (
                    description
                )}
            </div>
            
            <div className="ai-metadata">
                <span className="meta-tag">Condition: {isEditing ? 
                    <select value={condition} onChange={e => setCondition(e.target.value)}>
                        <option>Good</option><option>Fair</option><option>Poor</option><option>Critical</option><option>Unknown</option>
                    </select> : condition
                }</span>
                <span className="meta-tag">Confidence: {(problem.confidence * 100).toFixed(0)}%</span>
                {problem.requires_inspection && <span className="meta-tag alert">Requires Inspection</span>}
            </div>

            <div className="impacts">
                <div className="impact-box student-impact">
                    <strong>Student Impact:</strong> {problem.student_impact.level}
                </div>
                <div className="impact-box teacher-impact">
                    <strong>Teacher Impact:</strong> {problem.teacher_impact.level}
                </div>
            </div>

            <div className="admin-review-section">
                <h4>Administrator Review</h4>
                
                <div className="review-controls">
                    <select value={priority} onChange={e => setPriority(e.target.value)}>
                        <option value="">Set Human Priority...</option>
                        <option value="Critical">Critical</option>
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                    </select>

                    <input 
                        type="text" 
                        placeholder="Add review notes or evidence..." 
                        value={notes}
                        onChange={e => setNotes(e.target.value)}
                    />
                </div>

                <div className="action-buttons">
                    <button className="btn confirm" onClick={() => handleSaveReview('Confirmed')}><FiCheck /> Confirm</button>
                    <button className="btn reject" onClick={() => handleSaveReview('Rejected')}><FiX /> Reject</button>
                    <button className="btn edit" onClick={() => isEditing ? handleSaveReview('Modified') : setIsEditing(true)}>
                        {isEditing ? <><FiSave /> Save Edits</> : <><FiEdit /> Edit Findings</>}
                    </button>
                </div>
            </div>
        </div>
    );
};

export const ManualProblemFlagging: React.FC<{schoolId: string, imageId: string, imageUrl?: string}> = ({schoolId, imageId, imageUrl}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [title, setTitle] = useState('');
    const [category, setCategory] = useState('Other');
    const [description, setDescription] = useState('');
    const [priority, setPriority] = useState('Medium');
    const [coordinates, setCoordinates] = useState<{x: number, y: number} | null>(null);

    const handleImageClick = (e: React.MouseEvent<HTMLImageElement>) => {
        const rect = e.currentTarget.getBoundingClientRect();
        // Store relative coordinates (percentages)
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        setCoordinates({x, y});
    };

        const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            // Check if imageId is a valid UUID format before sending
            const isValidUuid = imageId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(imageId);

            await axios.post(`http://localhost:8000/api/v1/problems/school/${schoolId}/manual`, {
                image_id: isValidUuid ? imageId : null,
                title,
                category,
                description,
                human_priority: priority,
                image_coordinates: coordinates
            });
            alert("Manual problem flagged successfully!");
            setIsOpen(false);
            // Reset form fields
            setTitle(''); 
            setDescription(''); 
            setCoordinates(null);
        } catch(error: any) {
            console.error("Failed to flag problem", error);
            alert("Failed to save manual flag: " + (error.response?.data?.detail?.[0]?.msg || error.message));
        }
    };

    if (!isOpen) {
        return (
            <button className="manual-flag-btn" onClick={() => setIsOpen(true)}>
                <FiFlag /> AI missed something? Flag an issue manually
            </button>
        );
    }

    return (
        <div className="manual-flag-container">
            <h4>Manual Problem Flagging</h4>
            
            {imageUrl && (
                <div className="clickable-image-container">
                    <p className="instruction">Click on the image to pinpoint the problem area.</p>
                    <div style={{ position: 'relative', display: 'inline-block' }}>
                        <img 
                            src={imageUrl} 
                            alt="Pinpoint issue" 
                            onClick={handleImageClick}
                            className="clickable-image" 
                            style={{maxWidth: '100%', cursor: 'crosshair', borderRadius: '4px'}}
                        />
                        {coordinates && (
                            <div 
                                className="coordinate-marker" 
                                style={{
                                    position: 'absolute', 
                                    left: `${coordinates.x}%`, 
                                    top: `${coordinates.y}%`,
                                    width: '12px', height: '12px',
                                    backgroundColor: 'red',
                                    borderRadius: '50%',
                                    transform: 'translate(-50%, -50%)',
                                    border: '2px solid white'
                                }}
                            />
                        )}
                    </div>
                </div>
            )}

            <form className="manual-flag-form" onSubmit={handleSubmit}>
                <input required placeholder="Problem Title (e.g. Exposed Wiring)" value={title} onChange={e=>setTitle(e.target.value)} />
                <select value={category} onChange={e=>setCategory(e.target.value)}>
                    <option>Furniture</option><option>Electricity</option><option>Sanitation</option><option>Other</option>
                </select>
                <textarea required placeholder="Detailed description of what you observe in the image" value={description} onChange={e=>setDescription(e.target.value)} />
                <select value={priority} onChange={e=>setPriority(e.target.value)}>
                    <option>Critical</option><option>High</option><option>Medium</option><option>Low</option>
                </select>
                <div className="form-actions">
                    <button type="button" onClick={() => {setIsOpen(false); setCoordinates(null);}}>Cancel</button>
                    <button type="submit" className="btn confirm">Save Manual Flag</button>
                </div>
            </form>
        </div>
    );
};
