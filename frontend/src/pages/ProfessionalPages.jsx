import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  EmptyState,
  InfoNotice,
  MultiChoiceField,
  PageHeading,
  PrimaryButton,
  SectionCard,
  TextField,
} from '../components/Shared';

export function ProfessionalCasesPage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('Todos');
  return (
    <>
      <PageHeading eyebrow="PANEL PROFESIONAL" title="Casos de ECG" description="Consulte los casos asignados, su estado de revisión y la prioridad definida por el modelo." />
      <SectionCard>
        <div className="tv-form-grid">
          <TextField label="Buscar participante o caso" name="case-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Código de participante o caso" />
          <label className="tv-field" htmlFor="case-status"><span className="tv-field-label">Estado</span><select id="case-status" className="tv-input" value={status} onChange={(e) => setStatus(e.target.value)}><option>Todos</option><option>Pendiente</option><option>Validado</option><option>Modificado</option></select></label>
        </div>
      </SectionCard>
      <EmptyState title="Aún no hay casos conectados" description={`La lista se llenará cuando Django exponga los casos asignados. Filtro activo: ${status}${search ? ` · Búsqueda: ${search}` : ''}.`} />
      <InfoNotice>La prioridad IA, las etiquetas de referencia PTB-XL y los estados Pendiente, Validado y Modificado todavía no se consultan desde una API.</InfoNotice>
    </>
  );
}

export function ProfessionalCaseDetailPage() {
  const { caseId } = useParams();
  const [notes, setNotes] = useState('');
  const [editable, setEditable] = useState(false);
  const [classes, setClasses] = useState([]);
  const [message, setMessage] = useState('');
  const options = ['NORM', 'MI', 'STTC', 'CD', 'HYP'];

  function toggleClass(value) {
    setClasses((current) => current.includes(value) ? current.filter((item) => item !== value) : [...current, value]);
  }

  return (
    <>
      <PageHeading eyebrow="PANEL PROFESIONAL" title="Detalle del caso" description={`Caso: ${caseId}`} action={<Link to="/profesional/casos" className="tv-button tv-button-secondary">← Volver a casos</Link>} />
      <div className="tv-professional-detail-grid">
        <SectionCard>
          <h2>Trazado de 12 derivaciones</h2>
          <div className="tv-ecg-placeholder"><span>♡</span><strong>Visualizador ECG pendiente</strong><small>El archivo y la representación de las 12 derivaciones se cargarán desde el backend.</small></div>
        </SectionCard>
        <SectionCard>
          <h2>Informe de la IA</h2>
          {options.map((item) => <div className="tv-prof-result-row" key={item}><strong>{item}</strong><span>Sin resultado</span></div>)}
          <InfoNotice tone="warning">No hay salida del modelo conectada para este caso.</InfoNotice>
          <h3>Etiqueta de referencia PTB-XL</h3>
          <p className="tv-muted">Pendiente de consulta del conjunto de datos.</p>
        </SectionCard>
      </div>
      <SectionCard>
        <div className="tv-section-heading"><div><h2>Revisión profesional</h2><p className="tv-muted">La edición se habilita como demostración de interfaz.</p></div><span className="tv-status-pill">Pendiente</span></div>
        <label className="tv-field" htmlFor="professional-notes"><span className="tv-field-label">Notas del profesional (máximo 500 caracteres)</span><textarea id="professional-notes" className="tv-input tv-textarea" maxLength={500} value={notes} onChange={(e) => setNotes(e.target.value)} disabled={!editable} /></label>
        <MultiChoiceField label="Superclases corregidas" value={classes} onChange={setClasses} options={options} />
        <p className="tv-muted">Seleccionadas: {classes.length ? classes.join(', ') : 'Ninguna'}.</p>
        <div className="tv-button-row">
          <button className="tv-button tv-button-secondary" onClick={() => { setEditable(true); setMessage('Edición habilitada solo en esta sesión del navegador.'); }}>Modificar análisis</button>
          <PrimaryButton onClick={() => setMessage('Validación de demostración: no se ha guardado en el servidor.')}>Validar análisis</PrimaryButton>
          <PrimaryButton onClick={() => setMessage('Cambios de demostración: aún no existe un endpoint para guardar la revisión.')}>Guardar cambios</PrimaryButton>
        </div>
        {message && <InfoNotice tone="warning">{message}</InfoNotice>}
      </SectionCard>
    </>
  );
}
