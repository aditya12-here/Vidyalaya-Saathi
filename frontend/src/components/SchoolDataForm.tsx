import React, { useState } from 'react';
import axios from 'axios';
import './SchoolDataForm.css';

interface SchoolDataFormProps {
    onSchoolCreated: (schoolId: string) => void;
}

export const SchoolDataForm: React.FC<SchoolDataFormProps> = ({ onSchoolCreated }) => {
    const [schoolId, setSchoolId] = useState('');
    const [name, setName] = useState('');
    const [code, setCode] = useState('');
    const [state, setState] = useState('');
    const [district, setDistrict] = useState('');
    const [schoolType, setSchoolType] = useState('Primary');
    const [enrollment, setEnrollment] = useState<number | ''>('');
    const [teachers, setTeachers] = useState<number | ''>('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const response = await axios.post('http://localhost:8000/api/v1/school-data/schools', {
                school_id: schoolId.trim(),
                name,
                school_code: code.trim() || undefined,
                state: state.trim() || undefined,
                district: district.trim() || undefined,
                school_type: schoolType,
                total_enrollment: enrollment === '' ? undefined : enrollment,
                num_teachers: teachers === '' ? undefined : teachers
            });
            onSchoolCreated(response.data.school_id);
            alert("School profile saved successfully!");
        } catch (error: any) {
            console.error("Failed to save school", error);
            const errorDetail = error.response?.data?.detail 
                ? (typeof error.response.data.detail === 'string' 
                    ? error.response.data.detail 
                    : JSON.stringify(error.response.data.detail))
                : error.message;
            alert(`Error saving school profile: ${errorDetail}`);
        }
    };

    return (
        <div className="school-form-container">
            <h2>Register School Profile</h2>
            <form onSubmit={handleSubmit} className="school-form">
                <div className="form-group">
                    <label>Active School ID *</label>
                    <input required value={schoolId} onChange={e => setSchoolId(e.target.value)} placeholder="Enter assigned School ID" />
                </div>
                <div className="form-group">
                    <label>School Name *</label>
                    <input required value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Govt Primary School" />
                </div>
                
                <div className="form-row">
                    <div className="form-group">
                        <label>School Code (Optional)</label>
                        <input value={code} onChange={e => setCode(e.target.value)} placeholder="UDISE code" />
                    </div>
                    <div className="form-group">
                        <label>Type</label>
                        <select value={schoolType} onChange={e => setSchoolType(e.target.value)}>
                            <option>Primary</option>
                            <option>Upper Primary</option>
                            <option>Secondary</option>
                            <option>Senior Secondary</option>
                        </select>
                    </div>
                </div>

                <div className="form-row">
                    <div className="form-group">
                        <label>State</label>
                        <input value={state} onChange={e => setState(e.target.value)} />
                    </div>
                    <div className="form-group">
                        <label>District</label>
                        <input value={district} onChange={e => setDistrict(e.target.value)} />
                    </div>
                </div>

                <div className="form-row">
                    <div className="form-group">
                        <label>Total Enrollment</label>
                        <input 
                            type="number" 
                            min="0" 
                            value={enrollment === '' ? '' : enrollment} 
                            onChange={e => {
                                const val = parseInt(e.target.value);
                                setEnrollment(isNaN(val) ? '' : val);
                            }} 
                        />
                    </div>
                    <div className="form-group">
                        <label>Number of Teachers</label>
                        <input 
                            type="number" 
                            min="0" 
                            value={teachers === '' ? '' : teachers} 
                            onChange={e => {
                                const val = parseInt(e.target.value);
                                setTeachers(isNaN(val) ? '' : val);
                            }} 
                        />
                    </div>
                </div>

                <button type="submit" className="submit-btn">Save School Profile</button>
            </form>
        </div>
    );
};
