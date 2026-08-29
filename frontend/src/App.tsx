import { useState } from 'react';
import './App.css';
import { SchoolDataForm } from './components/SchoolDataForm';
import { ModuleUpload } from './components/ModuleUpload';

function App() {
  const [activeSchoolId, setActiveSchoolId] = useState<string | null>(null);

  // Allow manual entry logic for the dashboard notice
  const handleManualIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setActiveSchoolId(e.target.value);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Vidyalaya Saathi</h1>
      </header>
      <main className="App-main">
        {!activeSchoolId ? (
            <SchoolDataForm onSchoolCreated={setActiveSchoolId} />
        ) : (
            <div className="dashboard-container">
                <div className="dashboard-notice">
                    <label style={{fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px'}}>
                        Active School ID: 
                        <input 
                            value={activeSchoolId} 
                            onChange={handleManualIdChange}
                            placeholder="Enter assigned School ID"
                            style={{padding: '5px', borderRadius: '4px', border: '1px solid #ccc', minWidth: '300px'}}
                        />
                    </label>
                    <button onClick={() => setActiveSchoolId(null)} className="switch-school-btn">Change School</button>
                </div>
                
                <div className="placeholder-modules">
                    <div className="module-card">
                        <h3>FLN & Student Data Module</h3>
                        <p className="coming-soon">Coming Soon</p>
                        <ModuleUpload activeSchoolId={activeSchoolId} moduleName="FLN & Student Data" />
                    </div>
                    
                    <div className="module-card">
                        <h3>Teacher Workload Module</h3>
                        <p className="coming-soon">Coming Soon</p>
                        <ModuleUpload activeSchoolId={activeSchoolId} moduleName="Teacher Workload" />
                    </div>
                    
                    <div className="module-card">
                        <h3>Infrastructure Module</h3>
                        <p className="coming-soon">Coming Soon</p>
                        <ModuleUpload activeSchoolId={activeSchoolId} moduleName="Infrastructure" />
                    </div>
                </div>
            </div>
        )}
      </main>
    </div>
  );
}

export default App;
