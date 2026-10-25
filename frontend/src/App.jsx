import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000';

function App() {
  const [files, setFiles] = useState([]);
  const [manual, setManual] = useState(null);
  const [matchThreshold, setMatchThreshold] = useState(0.80);
  const [flagThreshold, setFlagThreshold] = useState(0.85);
  const [explain, setExplain] = useState(true);
  const [minRingSize, setMinRingSize] = useState(3);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  
  const [selectedPair, setSelectedPair] = useState(null);
  const [studentFilter, setStudentFilter] = useState('');
  const [showTemplateDetails, setShowTemplateDetails] = useState(false);

  const fileInputRef = useRef(null);
  const manualInputRef = useRef(null);

  // Close modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setSelectedPair(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleFileSelect = (e) => {
    if (e.target.files) {
      const selected = Array.from(e.target.files);
      setFiles((prev) => [...prev, ...selected]);
    }
  };

  const removeFile = (indexToRemove) => {
    setFiles((prev) => prev.filter((_, idx) => idx !== indexToRemove));
  };

  const handleManualSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setManual(e.target.files[0]);
    }
  };

  const removeManual = () => {
    setManual(null);
    if (manualInputRef.current) manualInputRef.current.value = '';
  };

  const runAnalysis = async () => {
    if (files.length === 0) {
      setError('Please select at least one student submission file to analyze.');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    if (manual) {
      formData.append('manual', manual);
    }

    formData.append('threshold', flagThreshold.toString());
    formData.append('match_threshold', matchThreshold.toString());
    formData.append('explain', explain.toString());
    formData.append('min_ring_size', minRingSize.toString());

    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || errData.error || `Server returned ${res.status}`);
      }

      const data = await res.json();
      setResults(data);
    } catch (err) {
      console.error('Analysis failed:', err);
      setError(err.message || 'Failed to connect to backend service. Ensure FastAPI server is running on localhost:8000.');
    } finally {
      setLoading(false);
    }
  };

  // Filter flagged pairs
  const filteredPairs = results?.flagged_pairs?.filter((pair) => {
    if (!studentFilter.trim()) return true;
    const q = studentFilter.toLowerCase();
    return (
      pair.student_a.toLowerCase().includes(q) ||
      pair.student_b.toLowerCase().includes(q) ||
      (pair.label && pair.label.toLowerCase().includes(q))
    );
  }) || [];

  const getLabelClass = (label) => {
    if (!label) return 'unclassified';
    const norm = label.toLowerCase();
    if (norm.includes('likely copy')) return 'likely-copy';
    if (norm.includes('paraphrase')) return 'paraphrase';
    if (norm.includes('shared source')) return 'shared-source';
    if (norm.includes('coincidence')) return 'coincidence';
    return 'unclassified';
  };

  const getScoreBadgeClass = (score) => {
    if (score >= 0.95) return 'high';
    if (score >= 0.85) return 'medium';
    return 'normal';
  };

  // Simple text highlight function for matched passages in modal
  const renderHighlightedPassage = (text) => {
    return <div className="passage-text">{text}</div>;
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
              <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
              <line x1="12" y1="22.08" x2="12" y2="12"></line>
            </svg>
          </div>
          <div>
            <h1 className="brand-title">Local Echo Scan</h1>
            <p className="brand-tagline">Student data never leaves this laptop.</p>
          </div>
        </div>
        <div className="privacy-badge">
          <span className="pulse-dot"></span>
          100% Local • Zero Cloud • Air-Gapped
        </div>
      </header>

      {/* Advisory Banner */}
      <aside className="advisory-banner">
        <div className="advisory-icon">ℹ</div>
        <div>
          <div className="advisory-title">This is evidence to review, not a verdict.</div>
          <div className="advisory-desc">
            Local Echo Scan flags text similarities for human evaluation. Academic judgment and integrity decisions always remain with the instructor.
          </div>
        </div>
      </aside>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Upload and Configuration Card */}
      <section className="upload-card">
        <div className="section-header">
          <h2 className="section-title">Scan Submissions</h2>
          <p className="section-subtitle">Select student lab records or assignment files to begin local similarity analysis</p>
        </div>

        <div className="dropzone-grid">
          {/* Submissions Dropzone */}
          <div 
            className="dropzone"
            onClick={() => fileInputRef.current?.click()}
          >
            <input 
              type="file" 
              multiple 
              ref={fileInputRef} 
              style={{ display: 'none' }}
              onChange={handleFileSelect}
              accept=".pdf,.docx,.txt,.py,.c,.cpp,.java,.js,.ts"
            />
            <div className="dropzone-icon">📁</div>
            <div className="dropzone-title">Student Submissions</div>
            <div className="dropzone-hint">PDF, DOCX, TXT or code files • Click or drag to add</div>

            {files.length > 0 && (
              <div className="files-preview" onClick={(e) => e.stopPropagation()}>
                {files.map((f, idx) => (
                  <span key={idx} className="file-chip">
                    {f.name}
                    <span 
                      className="file-chip-remove" 
                      onClick={() => removeFile(idx)}
                      title="Remove file"
                    >
                      ×
                    </span>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Optional Lab Manual Dropzone */}
          <div 
            className="dropzone"
            onClick={() => manualInputRef.current?.click()}
          >
            <input 
              type="file" 
              ref={manualInputRef} 
              style={{ display: 'none' }}
              onChange={handleManualSelect}
              accept=".pdf,.docx,.txt"
            />
            <div className="dropzone-icon">📖</div>
            <div className="dropzone-title">Lab Manual (Optional)</div>
            <div className="dropzone-hint">Template paragraphs will be auto-ignored</div>

            {manual && (
              <div className="files-preview" onClick={(e) => e.stopPropagation()}>
                <span className="file-chip" style={{ borderColor: 'var(--amber-border)', color: 'var(--amber)' }}>
                  {manual.name}
                  <span 
                    className="file-chip-remove" 
                    onClick={removeManual}
                    title="Remove manual"
                  >
                    ×
                  </span>
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Parameters Grid */}
        <div className="parameters-panel">
          <div className="param-group">
            <div className="param-label-row">
              <span className="param-label">Match Threshold</span>
              <span className="param-val">{(matchThreshold * 100).toFixed(0)}%</span>
            </div>
            <input 
              type="range" 
              min="0.50" 
              max="1.00" 
              step="0.01" 
              value={matchThreshold}
              onChange={(e) => setMatchThreshold(parseFloat(e.target.value))}
              className="slider-input"
            />
          </div>

          <div className="param-group">
            <div className="param-label-row">
              <span className="param-label">Flag Threshold</span>
              <span className="param-val">{(flagThreshold * 100).toFixed(0)}%</span>
            </div>
            <input 
              type="range" 
              min="0.50" 
              max="1.00" 
              step="0.01" 
              value={flagThreshold}
              onChange={(e) => setFlagThreshold(parseFloat(e.target.value))}
              className="slider-input"
            />
          </div>

          <div className="param-group">
            <div className="param-label-row">
              <span className="param-label">Min Ring Size</span>
              <span className="param-val">{minRingSize} students</span>
            </div>
            <input 
              type="range" 
              min="2" 
              max="6" 
              step="1" 
              value={minRingSize}
              onChange={(e) => setMinRingSize(parseInt(e.target.value, 10))}
              className="slider-input"
            />
          </div>

          <div className="toggle-group">
            <div className="toggle-label-wrap">
              <span className="toggle-title">Explain with Gemma</span>
              <span className="toggle-desc">Local Ollama explanations</span>
            </div>
            <label className="switch">
              <input 
                type="checkbox" 
                checked={explain} 
                onChange={(e) => setExplain(e.target.checked)}
              />
              <span className="slider-round"></span>
            </label>
          </div>
        </div>

        {/* Action Row */}
        <div className="action-row">
          <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            {files.length} file{files.length === 1 ? '' : 's'} selected
          </span>
          <button 
            className="analyze-btn" 
            onClick={runAnalysis}
            disabled={loading || files.length === 0}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Analyzing locally...
              </>
            ) : (
              <>
                <span>▶</span>
                Run Echo Scan
              </>
            )}
          </button>
        </div>
      </section>

      {/* Results View */}
      {results && (
        <>
          {/* Offline Notice if applicable */}
          {explain && results.explanations_available === false && (
            <div className="offline-notice">
              <span>⚡</span>
              <div>
                <strong>Gemma explanations unavailable:</strong> Ollama server at localhost:11434 was offline or timed out. Local similarity calculations and copy ring clustering are complete.
              </div>
            </div>
          )}

          {/* Metrics Summary Bar */}
          <div className="metrics-bar">
            <div className="metric-card">
              <div className="metric-title">Files Scanned</div>
              <div className="metric-val">{results.summary.total_files}</div>
              <div className="metric-sub">{results.summary.total_paragraphs_after_cleaning} cleaned passages</div>
            </div>
            <div className="metric-card">
              <div className="metric-title">Ignored Boilerplate</div>
              <div className="metric-val">{results.template_removal.removed_count}</div>
              <div className="metric-sub">paragraphs excluded</div>
            </div>
            <div className={`metric-card ${results.flagged_pairs.length > 0 ? 'highlight' : ''}`}>
              <div className="metric-title">Flagged for Review</div>
              <div className="metric-val" style={{ color: results.flagged_pairs.length > 0 ? 'var(--rose)' : 'inherit' }}>
                {results.flagged_pairs.length}
              </div>
              <div className="metric-sub">pairs exceeding threshold</div>
            </div>
            <div className={`metric-card ${results.copy_rings.length > 0 ? 'highlight' : ''}`}>
              <div className="metric-title">Copy Rings</div>
              <div className="metric-val" style={{ color: results.copy_rings.length > 0 ? 'var(--cyan)' : 'inherit' }}>
                {results.copy_rings.length}
              </div>
              <div className="metric-sub">clusters of ≥ {minRingSize} students</div>
            </div>
          </div>

          {/* Copy Rings Section */}
          {results.copy_rings && results.copy_rings.length > 0 && (
            <section className="rings-container">
              <h2 className="section-title">Detected Copy Rings ({results.copy_rings.length})</h2>
              <div className="rings-grid">
                {results.copy_rings.map((ring, idx) => (
                  <div key={idx} className="ring-card">
                    <div className="ring-header">
                      <span className="ring-badge">Ring #{idx + 1} • {ring.size} Students</span>
                      <span className="ring-score">Avg Score: {(ring.average_score * 100).toFixed(1)}%</span>
                    </div>
                    <div className="ring-desc">{ring.description} ({ring.pair_count} internal pairs)</div>
                    <div className="ring-members-list">
                      {ring.members.map((m, mIdx) => (
                        <span 
                          key={mIdx} 
                          className="ring-member-tag"
                          style={{ cursor: 'pointer' }}
                          onClick={() => setStudentFilter(m)}
                          title="Click to filter flagged pairs for this student"
                        >
                          👤 {m}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Flagged Pairs Section */}
          <section className="pairs-section">
            <div className="pairs-header-row">
              <h2 className="section-title">
                Flagged Student Pairs ({filteredPairs.length})
              </h2>
              <input 
                type="text" 
                placeholder="Filter by student name..."
                value={studentFilter}
                onChange={(e) => setStudentFilter(e.target.value)}
                className="pairs-filter-input"
              />
            </div>

            {filteredPairs.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">✓</div>
                <div className="empty-state-title">No similar pairs found</div>
                <div className="empty-state-desc">
                  {studentFilter ? 'No flagged pairs match the filter criteria.' : 'All student submissions appear independent based on the selected thresholds.'}
                </div>
              </div>
            ) : (
              <div className="pairs-list">
                {filteredPairs.map((pair, pIdx) => {
                  const scorePct = (pair.score * 100).toFixed(1);
                  const firstMatch = pair.matched_passages?.[0];

                  return (
                    <div 
                      key={pIdx} 
                      className="pair-card"
                      onClick={() => setSelectedPair(pair)}
                    >
                      <div className="pair-card-top">
                        <div className="pair-students">
                          <span className="student-name">{pair.student_a}</span>
                          <span className="pair-arrow">⟷</span>
                          <span className="student-name">{pair.student_b}</span>
                        </div>
                        <div className="pair-badges">
                          <span className={`score-badge ${getScoreBadgeClass(pair.score)}`}>
                            {scorePct}% Similar
                          </span>
                          <span className="match-count-badge">
                            {pair.match_count} passage{pair.match_count === 1 ? '' : 's'}
                          </span>
                          {pair.label && (
                            <span className={`gemma-badge ${getLabelClass(pair.label)}`}>
                              {pair.label}
                            </span>
                          )}
                        </div>
                      </div>

                      {pair.reason && (
                        <div className="pair-reason">
                          "{pair.reason}"
                        </div>
                      )}

                      {firstMatch && (
                        <div className="pair-passage-preview">
                          <strong>Match Preview: </strong>
                          {firstMatch.text_a}
                        </div>
                      )}

                      <div className="pair-card-footer">
                        <span className="review-link">
                          Review matching passages side-by-side →
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Ignored Template Section (Accordion) */}
          {results.template_removal && (
            <section className="template-section">
              <div 
                className="template-header"
                onClick={() => setShowTemplateDetails(!showTemplateDetails)}
              >
                <div className="template-header-title">
                  <span>Ignored Template & Boilerplate Text</span>
                  <span className="template-count-pill">
                    {results.template_removal.removed_count} removed
                  </span>
                </div>
                <div>{showTemplateDetails ? '▲ Hide' : '▼ View Details'}</div>
              </div>

              {showTemplateDetails && (
                <div className="template-body">
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                    {results.template_removal.boilerplate_detected} common boilerplate patterns detected across submissions.
                  </div>
                  {results.template_removal.removed_paragraphs.map((rp, rIdx) => (
                    <div key={rIdx} className="template-item">
                      <div className="template-item-top">
                        <span>Source: {rp.student}</span>
                        <span>Reason: {rp.reason}</span>
                      </div>
                      <div className="template-item-text">{rp.text}</div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}

      {/* Side-by-Side Comparison Modal */}
      {selectedPair && (
        <div className="modal-overlay" onClick={() => setSelectedPair(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <span>{selectedPair.student_a}</span>
                <span style={{ color: 'var(--text-muted)' }}>vs</span>
                <span>{selectedPair.student_b}</span>
              </div>
              <button 
                className="modal-close-btn" 
                onClick={() => setSelectedPair(null)}
              >
                ✕
              </button>
            </div>

            <div className="modal-subinfo">
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <span className={`score-badge ${getScoreBadgeClass(selectedPair.score)}`}>
                  {(selectedPair.score * 100).toFixed(1)}% Composite Score
                </span>
                {selectedPair.label && (
                  <span className={`gemma-badge ${getLabelClass(selectedPair.label)}`}>
                    {selectedPair.label}
                  </span>
                )}
                <span className="match-count-badge">
                  {selectedPair.matched_passages?.length || 0} matching passages
                </span>
              </div>
              {selectedPair.reason && (
                <div className="modal-reason">
                  "{selectedPair.reason}"
                </div>
              )}
            </div>

            <div className="modal-body">
              {selectedPair.matched_passages?.map((match, mIdx) => (
                <div key={mIdx} className="passage-match-card">
                  <div className="passage-match-header">
                    <span className="passage-index">Passage Match #{mIdx + 1}</span>
                    <span className="passage-sim-badge">
                      {(match.similarity * 100).toFixed(1)}% Cosine Similarity
                    </span>
                  </div>
                  <div className="side-by-side-grid">
                    <div className="passage-column">
                      <div className="passage-student-tag">{selectedPair.student_a}</div>
                      {renderHighlightedPassage(match.text_a)}
                    </div>
                    <div className="passage-column" style={{ borderLeft: '1px solid var(--border-subtle)' }}>
                      <div className="passage-student-tag">{selectedPair.student_b}</div>
                      {renderHighlightedPassage(match.text_b)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
