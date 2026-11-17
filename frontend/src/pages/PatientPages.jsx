import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ChoiceField,
  EmptyState,
  InfoNotice,
  PageHeading,
  PrimaryButton,
  SectionCard,
  SecondaryButton,
  SelectField,
} from '../components/Shared';
import { api, getApiErrorMessage, getStoredUser } from '../services/api';
import {
  displayHistoryValue,
  displayRecommendationCategory,
  fromClarityCode,
  fromProfilePayload,
  historyCategoryValues,
  toClarityCode,
  toMorningPayload,
  toNightPayload,
} from '../services/mappers';

export function HomePage() {
  const user = getStoredUser();
  return (
    <>
      <div className="tv-welcome-panel">
        <p className="tv-eyebrow">SU SALUD, A SU RITMO</p>
        <h1>Hola{user?.nombre ? `, ${user.nombre}` : ''}</h1>
        <p>Pequeños hábitos pueden ayudarle a cuidar su bienestar cardiovascular.</p>
        <span className="tv-heartline" aria-hidden="true">♡</span>
      </div>
      <div className="tv-section-heading"><div><p className="tv-eyebrow">SU ESPACIO PERSONAL</p><h2>¿Qué desea hacer hoy?</h2></div></div>
      <div className="tv-dashboard-grid">
        <Link to="/habitos" className="tv-dashboard-card">
          <span className="tv-dashboard-icon tv-icon-mint">✓</span><strong>Registro diario</strong><p>Registre cómo durmió y cómo fue su día.</p><span className="tv-card-arrow">Abrir módulo →</span>
        </Link>
        <Link to="/ecg" className="tv-dashboard-card">
          <span className="tv-dashboard-icon tv-icon-red">♡</span><strong>Cargar ECG</strong><p>Consulte el caso de prueba que le asignó el equipo.</p><span className="tv-card-arrow">Abrir módulo →</span>
        </Link>
        <Link to="/consejos" className="tv-dashboard-card">
          <span className="tv-dashboard-icon tv-icon-mint">✦</span><strong>Recomendaciones</strong><p>Revise orientaciones relacionadas con sus hábitos.</p><span className="tv-card-arrow">Ver consejos →</span>
        </Link>
        <Link to="/historial" className="tv-dashboard-card">
          <span className="tv-dashboard-icon tv-icon-mint">▤</span><strong>Historial de hábitos</strong><p>Consulte sus registros anteriores.</p><span className="tv-card-arrow">Ver historial →</span>
        </Link>
      </div>
      <InfoNotice>Sus registros se consultan desde su cuenta y se guardan en el backend.</InfoNotice>
    </>
  );
}

export function HabitsPage() {
  return (
    <>
      <PageHeading eyebrow="REGISTRO DIARIO" title="¿Cómo ha estado?" description="La plataforma organiza dos encuestas breves. Puede responder ambas; el horario de su perfil ayuda a sugerir cuál hacer primero." />
      <div className="tv-survey-choice-list">
        <Link to="/habitos/manana" className="tv-survey-choice-card">
          <span className="tv-survey-emoji">☀</span>
          <div><strong>Encuesta de la mañana</strong><p>El sueño de anoche · Menos de 30 segundos</p></div>
          <span className="tv-card-arrow">→</span>
        </Link>
        <Link to="/habitos/noche" className="tv-survey-choice-card">
          <span className="tv-survey-emoji">☾</span>
          <div><strong>Encuesta de la noche</strong><p>Cómo fue su día · Menos de 40 segundos</p></div>
          <span className="tv-card-arrow">→</span>
        </Link>
      </div>
      <SectionCard>
        <h2>¿Ya registró sus hábitos?</h2>
        <p className="tv-muted">Revise sus respuestas anteriores en el historial.</p>
        <SecondaryButton to="/historial">Ver historial</SecondaryButton>
      </SectionCard>
    </>
  );
}

const morningQuestions = [
  { key: 'sleepHours', label: '¿Cuántas horas durmió anoche?', options: ['Menos de 5', '5–6', '6–7', '7–9', 'Más de 9'] },
  { key: 'awakenings', label: '¿Se despertó durante la noche?', options: ['No', '1 vez', '2 o 3 veces', 'Muchas veces'] },
  { key: 'bathroom', label: '¿Se levantó al baño en la noche?', options: ['No', '1 vez', '2 o más veces'] },
  { key: 'feeling', label: '¿Cómo se sintió al despertar?', options: ['Descansado(a)', 'Más o menos', 'Cansado(a)'] },
  { key: 'bedtime', label: '¿A qué hora se acostó? (opcional)', options: ['Antes de las 10 p. m.', '10–11 p. m.', '11 p. m.–12 a. m.', 'Después de las 12'] },
];

const nightQuestions = [
  { key: 'nap', label: '¿Durmió siesta en la tarde?', options: ['No', 'Menos de 30 min', '30 a 60 min', 'Más de 1 hora'] },
  { key: 'walk', label: '¿Caminó hoy a paso rápido?', options: ['No', '10–20 min', '20–30 min', 'Más de 30 min'] },
  { key: 'exercise', label: '¿Hizo deporte o ejercicio?', options: ['No', 'Sí, suave (yoga, estiramiento)', 'Sí, moderado (bici, baile, trotar)', 'Sí, intenso'] },
  { key: 'sitting', label: '¿Pasó más de 6 horas sentado(a)?', options: ['Sí', 'No'] },
  { key: 'fruit', label: '¿Cuántas frutas y verduras comió hoy?', options: ['0', '1–2', '3–4', '5 o más'] },
  { key: 'processed', label: '¿Comió algo frito, de paquete o embutido?', options: ['No', 'Una vez', 'Varias veces'] },
  { key: 'sugary', label: '¿Tomó gaseosa, jugo de caja o algo con mucha azúcar?', options: ['No', '1 vaso', '2 o más'] },
  { key: 'water', label: '¿Cuántos vasos de agua tomó?', options: ['0–2', '3–5', '6–8', 'Más de 8'] },
  { key: 'salt', label: '¿Le puso sal extra a la comida?', options: ['No', 'Un poco', 'Sí, bastante'] },
  { key: 'stress', label: '¿Cómo estuvo su estrés hoy?', options: ['Bajo', 'Medio', 'Alto'] },
  { key: 'symptom', label: '¿Sintió hoy dolor en el pecho, falta de aire o palpitaciones?', options: ['No', 'Sí'] },
];

function SurveyPage({ mode }) {
  const navigate = useNavigate();
  const isMorning = mode === 'manana';
  const questions = isMorning ? morningQuestions : nightQuestions;
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(!isMorning);

  useEffect(() => {
    if (isMorning) return undefined;
    let active = true;
    api.profile.get()
      .then((data) => { if (active) setProfile(data); })
      .catch((requestError) => { if (active) setError(getApiErrorMessage(requestError)); })
      .finally(() => { if (active) setProfileLoading(false); });
    return () => { active = false; };
  }, [isMorning]);

  const conditionalQuestions = useMemo(() => {
    if (!profile) return [];
    const result = [];
    if (['OCASIONAL', 'DIARIO'].includes(profile.tabaquismo)) {
      result.push({ key: 'smoked', label: '¿Fumó hoy?', options: ['No', '1–5 cigarrillos', 'Más de 5'] });
    }
    if (profile.alcohol_semana && profile.alcohol_semana !== 'NUNCA') {
      result.push({ key: 'alcohol', label: '¿Tomó bebidas alcohólicas?', options: ['No', '1–2 tragos', '3 o más'] });
    }
    if (profile.toma_medicamentos && profile.toma_medicamentos !== 'NO') {
      result.push({ key: 'medication', label: '¿Tomó sus medicamentos?', options: ['Sí', 'Se me olvidó'] });
    }
    return result;
  }, [profile]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    const missing = questions.filter((question) => question.key !== 'bedtime' && !answers[question.key]);
    const missingConditional = conditionalQuestions.filter((question) => !answers[question.key]);
    if (missing.length || missingConditional.length) {
      setError('Responda todas las preguntas obligatorias antes de continuar.');
      return;
    }

    setLoading(true);
    try {
      if (isMorning) {
        await api.habits.submitMorning(toMorningPayload(answers));
        navigate('/consejos');
      } else {
        const response = await api.habits.submitNight(toNightPayload(answers, profile));
        if (response.alerta_urgencias) navigate('/urgencias');
        else navigate('/consejos');
      }
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow={isMorning ? 'ENCUESTA DE LA MAÑANA' : 'ENCUESTA DE LA NOCHE'}
        title={isMorning ? '¡Buenos días! ¿Cómo durmió?' : '¿Cómo le fue hoy?'}
        description={isMorning ? 'El sueño de anoche. Menos de 30 segundos; un toque por pregunta.' : 'Un repaso breve de su actividad, alimentación e hidratación.'}
      />
      {!isMorning && profileLoading && <InfoNotice>Cargando las preguntas que aplican según su perfil…</InfoNotice>}
      <form className="tv-form" onSubmit={handleSubmit}>
        {questions.map((question, index) => (
          <SectionCard key={question.key} className="tv-question-card">
            <span className="tv-question-index">{String(index + 1).padStart(2, '0')}</span>
            <ChoiceField
              label={question.label}
              name={question.key}
              value={answers[question.key] || ''}
              onChange={(value) => setAnswers((current) => ({ ...current, [question.key]: value }))}
              options={question.options}
            />
            {answers[question.key] && <p className="tv-answer-feedback">Respuesta seleccionada</p>}
          </SectionCard>
        ))}
        {!isMorning && conditionalQuestions.length > 0 && (
          <SectionCard>
            <h2>Preguntas adicionales según su perfil</h2>
            {conditionalQuestions.map((question) => (
              <ChoiceField
                key={question.key}
                label={question.label}
                name={question.key}
                value={answers[question.key] || ''}
                onChange={(value) => setAnswers((current) => ({ ...current, [question.key]: value }))}
                options={question.options}
              />
            ))}
          </SectionCard>
        )}
        {error && <InfoNotice tone="danger">{error}</InfoNotice>}
        <InfoNotice>Las respuestas se guardan en su registro diario. La retroalimentación personalizada se mostrará cuando esté conectado el motor de reglas y los mensajes revisados por el equipo de salud.</InfoNotice>
        <PrimaryButton type="submit" disabled={loading || profileLoading || (!isMorning && !profile)}>{loading ? 'Guardando respuestas…' : 'Guardar y ver recomendaciones'}</PrimaryButton>
      </form>
    </>
  );
}

export function MorningSurveyPage() { return <SurveyPage mode="manana" />; }
export function NightSurveyPage() { return <SurveyPage mode="noche" />; }

const historyFields = [
  { group: 'Sueño', fields: [['horas_sueno_anoche', 'Horas de sueño'], ['despertares_noche', 'Despertares'], ['idas_bano_noche', 'Idas al baño'], ['sensacion_despertar', 'Cómo despertó'], ['hora_acostarse_anoche', 'Hora de acostarse']] },
  { group: 'Actividad física', fields: [['siesta_tarde', 'Siesta'], ['caminata_hoy', 'Caminata rápida'], ['ejercicio_hoy', 'Ejercicio'], ['sentado_mas_6h', 'Más de 6 horas sentado']] },
  { group: 'Alimentación e hidratación', fields: [['frutas_verduras_hoy', 'Frutas y verduras'], ['fritos_paquete_hoy', 'Fritos, paquetes o embutidos'], ['bebida_azucarada_hoy', 'Bebidas azucaradas'], ['vasos_agua_respuesta', 'Vasos de agua'], ['sal_extra_hoy', 'Sal adicional']] },
  { group: 'Estrés y bienestar', fields: [['estres_hoy', 'Estrés'], ['sintoma_hoy', 'Síntoma reportado']] },
  { group: 'Tabaco, alcohol y medicamentos', fields: [['fumo_hoy', 'Tabaco'], ['alcohol_hoy', 'Alcohol'], ['medicamentos_hoy', 'Medicamentos']] },
];

function formatDate(dateValue) {
  if (!dateValue) return 'Fecha no disponible';
  const date = new Date(`${dateValue}T00:00:00`);
  return new Intl.DateTimeFormat('es-CO', { dateStyle: 'long' }).format(date);
}

function displayRecordValue(field, value) {
  if (field === 'sentado_mas_6h' || field === 'sintoma_hoy') {
    if (value === null || value === undefined) return null;
    return value ? 'Sí' : 'No';
  }
  return displayHistoryValue(field, value);
}

export function HistoryPage() {
  const [period, setPeriod] = useState('Últimos 7 días');
  const [category, setCategory] = useState('Todas');
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api.habits.list({ periodo: period === 'Últimos 7 días' ? '7' : period === 'Últimos 30 días' ? '30' : 'todo', categoria: historyCategoryValues[category] })
      .then((data) => { if (active) setRecords(Array.isArray(data) ? data : []); })
      .catch((requestError) => { if (active) setError(getApiErrorMessage(requestError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [period, category]);

  return (
    <>
      <PageHeading title="Historial de hábitos" description="Consulte sus registros por fecha y categoría." />
      <SectionCard>
        <div className="tv-form-grid">
          <SelectField label="Periodo" name="period" value={period} onChange={(e) => setPeriod(e.target.value)} options={['Últimos 7 días', 'Últimos 30 días', 'Todo']} />
          <SelectField label="Categoría" name="category" value={category} onChange={(e) => setCategory(e.target.value)} options={Object.keys(historyCategoryValues)} />
        </div>
        <p className="tv-field-helper">Periodo: {period === 'Todo' ? 'Todos los registros' : period}.</p>
      </SectionCard>
      {loading && <InfoNotice>Cargando historial…</InfoNotice>}
      {error && <InfoNotice tone="danger">{error}</InfoNotice>}
      {!loading && !error && records.length === 0 && (
        <EmptyState title="Aún no hay registros" description="No hay registros guardados para los filtros seleccionados." action={<SecondaryButton to="/habitos">Registrar hábitos</SecondaryButton>} />
      )}
      {!loading && !error && records.map((record) => (
        <SectionCard key={record.id} className="tv-history-card">
          <div className="tv-section-heading">
            <div><p className="tv-eyebrow">REGISTRO DIARIO</p><h2>{formatDate(record.fecha)}</h2></div>
            <span className="tv-status-pill">{record.manana_completada_en && record.noche_completada_en ? 'Completo' : 'Parcial'}</span>
          </div>
          {historyFields.map((group) => {
            const visible = group.fields
              .map(([field, label]) => ({ field, label, value: displayRecordValue(field, record[field]) }))
              .filter((item) => item.value !== null && item.value !== undefined && item.value !== '');
            if (!visible.length) return null;
            return (
              <div key={group.group} className="tv-history-group">
                <h3>{group.group}</h3>
                {visible.map((item) => <div className="tv-profile-row" key={item.field}><span>{item.label}</span><strong>{item.value}</strong></div>)}
              </div>
            );
          })}
        </SectionCard>
      ))}
    </>
  );
}

export function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingId, setLoadingId] = useState(null);
  const [error, setError] = useState('');
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    let active = true;
    api.recommendations.list()
      .then((data) => { if (active) setRecommendations(Array.isArray(data) ? data : []); })
      .catch((requestError) => { if (active) setError(getApiErrorMessage(requestError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function handleClarity(recommendationId, label) {
    setError('');
    setLoadingId(recommendationId);
    try {
      const updated = await api.recommendations.updateClarity(recommendationId, toClarityCode(label));
      setRecommendations((current) => current.map((item) => item.id === recommendationId ? updated : item));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <>
      <PageHeading title="Sus recomendaciones" description="Orientaciones preventivas relacionadas con hábitos registrados." />
      <InfoNotice>Las recomendaciones que aparecen aquí son las que el backend ha registrado como mostradas a su cuenta. Sus respuestas de claridad se guardan individualmente.</InfoNotice>
      {loading && <InfoNotice>Cargando recomendaciones…</InfoNotice>}
      {error && <InfoNotice tone="danger">{error}</InfoNotice>}
      {!loading && !error && recommendations.length === 0 && (
        <EmptyState title="Todavía no hay recomendaciones" description="Cuando el motor de reglas genere recomendaciones para sus registros, aparecerán en esta sección. No se muestran consejos de ejemplo como si fueran personalizados." action={<SecondaryButton to="/habitos">Registrar hábitos</SecondaryButton>} />
      )}
      <div className="tv-recommendation-list">
        {recommendations.map((recommendation) => (
          <SectionCard key={recommendation.id} className="tv-recommendation-card">
            <div className="tv-recommendation-topline"><span className="tv-category-pill">{displayRecommendationCategory(recommendation.categoria)}</span><span className="tv-recommendation-id">{recommendation.codigo}</span></div>
            <p className="tv-situation-label">Situación identificada</p>
            <p className="tv-situation-text">{recommendation.situacion_identificada}</p>
            <p className="tv-recommendation-text">{recommendation.texto_recomendacion}</p>
            <ChoiceField
              label="¿Le resultó clara esta recomendación?"
              name={`clarity-${recommendation.id}`}
              value={fromClarityCode(recommendation.respuesta_claridad)}
              onChange={(value) => handleClarity(recommendation.id, value)}
              options={['Sí', 'Más o menos', 'No']}
              columns={3}
            />
            {loadingId === recommendation.id && <p className="tv-answer-feedback">Guardando respuesta…</p>}
            {recommendation.respuesta_claridad && <p className="tv-answer-feedback">Respuesta registrada: {fromClarityCode(recommendation.respuesta_claridad)}.</p>}
          </SectionCard>
        ))}
      </div>
      <InfoNotice tone="warning">Estas recomendaciones no sustituyen una consulta médica.</InfoNotice>
      <SectionCard>
        <h2>¿Necesita apoyo emocional urgente?</h2>
        <p className="tv-muted">La base de conocimiento contempla una ruta de ayuda para situaciones de crisis de salud mental.</p>
        <button className="tv-text-link" onClick={() => setShowHelp((current) => !current)}>{showHelp ? 'Ocultar información' : 'Necesito ayuda ahora'}</button>
        {showHelp && <InfoNotice tone="danger">En Colombia, el documento indica la línea 192, opción 4, para teleorientación en salud mental. <a href="tel:192">Llamar al 192</a> y seleccionar la opción 4.</InfoNotice>}
      </SectionCard>
    </>
  );
}

export function EcgUploadPage() {
  const [file, setFile] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [message, setMessage] = useState('');
  function handleSubmit(event) {
    event.preventDefault();
    if (!file || !confirmed) {
      setMessage('Seleccione un archivo y confirme que corresponde a un caso de prueba.');
      return;
    }
    setMessage('Archivo seleccionado correctamente. La carga y el procesamiento ECG se conectarán en la siguiente etapa. No se ha generado ningún resultado.');
  }
  return (
    <>
      <PageHeading title="Cargar ECG" description="Seleccione el caso de prueba asignado por el equipo." />
      <form className="tv-form" onSubmit={handleSubmit}>
        <SectionCard>
          <h2>Caso asignado</h2>
          <div className="tv-assigned-case"><span className="tv-status-dot" /> <div><strong>Caso asignado por el equipo</strong><small>El listado se cargará desde el backend cuando se conecte esta pantalla.</small></div></div>
          <label className="tv-field" htmlFor="ecg-file">
            <span className="tv-field-label">Archivo del ECG de prueba <span className="tv-required">*</span></span>
            <input id="ecg-file" type="file" onChange={(e) => { setFile(e.target.files?.[0] || null); setMessage(''); }} className="tv-file-input" />
            <small className="tv-field-helper">La base funcional define una señal digital compatible con PTB-XL. El formato y tamaño máximo están pendientes de confirmación técnica.</small>
          </label>
          {file && <div className="tv-file-selected"><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(1)} KB</span></div>}
          <label className="tv-check-row tv-check-large"><input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} /><span>Entiendo que es un caso de prueba y no mi propio electrocardiograma.</span></label>
          <PrimaryButton type="submit">Enviar a análisis</PrimaryButton>
          {message && <InfoNotice tone={file && confirmed ? 'warning' : 'danger'}>{message}</InfoNotice>}
        </SectionCard>
      </form>
      <InfoNotice tone="warning">El modelo de IA no está integrado. Esta pantalla todavía no realiza análisis clínicos.</InfoNotice>
      <div className="tv-button-row"><SecondaryButton to="/ecg/procesando">Ver pantalla de procesamiento</SecondaryButton><SecondaryButton to="/ecg/resultado">Ver estructura del resultado</SecondaryButton></div>
    </>
  );
}

const ecgClasses = [
  ['NORM', 'Patrón sin hallazgos destacados'],
  ['MI', 'Patrón asociado a infarto'],
  ['STTC', 'Cambios en el segmento ST/T'],
  ['CD', 'Alteración en la conducción eléctrica'],
  ['HYP', 'Patrón de hipertrofia'],
];

export function EcgProcessingPage() {
  return (
    <>
      <PageHeading eyebrow="ESTADO DEL ECG" title="Procesamiento y validación" description="Esta pantalla representa los estados previstos para el caso asignado." />
      <SectionCard>
        <div className="tv-process-step"><span className="tv-process-number">1</span><div><strong>Validación del archivo</strong><p>Comprobar formato, integridad y legibilidad.</p><span className="tv-status-pill">Pendiente de backend</span></div></div>
        <div className="tv-process-step"><span className="tv-process-number">2</span><div><strong>Procesamiento del ECG</strong><p>Enviar la señal al servicio que ejecutará el modelo.</p><span className="tv-status-pill">Pendiente de integración</span></div></div>
        <div className="tv-process-step"><span className="tv-process-number">3</span><div><strong>Resultado</strong><p>Mostrar una respuesta por superclase cuando el servicio devuelva los datos.</p><span className="tv-status-pill">Sin resultado</span></div></div>
      </SectionCard>
      <h2 className="tv-subheading">Mensajes de error que debe manejar el backend</h2>
      <div className="tv-error-list">
        <InfoNotice tone="danger">Formato no permitido: informe qué formatos acepta el sistema.</InfoNotice>
        <InfoNotice tone="danger">Archivo ilegible o incompleto: permita seleccionar otro archivo.</InfoNotice>
        <InfoNotice tone="warning">Error de conexión: indique que el archivo no pudo enviarse.</InfoNotice>
        <InfoNotice tone="warning">Tiempo de respuesta excedido: permita reintentar o volver a la carga.</InfoNotice>
      </div>
      <InfoNotice>La meta de respuesta definida para el ECG es menor a 3 minutos, pero todavía no hay un servicio integrado con el modelo.</InfoNotice>
      <SecondaryButton to="/ecg">Elegir otro archivo</SecondaryButton>
    </>
  );
}

export function EcgResultPage() {
  const navigate = useNavigate();
  return (
    <>
      <PageHeading eyebrow="PANTALLA DE RESULTADO" title="Resultado experimental" description="Esta es la estructura visual prevista para mostrar las cinco superclases de PTB-XL." />
      <div className="tv-result-list">
        {ecgClasses.map(([code, label]) => <SectionCard key={code} className="tv-result-row"><div><strong>{code}</strong><p>{label}</p></div><span className="tv-result-value">Pendiente</span></SectionCard>)}
      </div>
      <InfoNotice tone="warning">No hay probabilidades disponibles. Los valores aparecerán únicamente cuando el backend reciba la salida del modelo. El resultado será experimental, no un diagnóstico.</InfoNotice>
      <PrimaryButton onClick={() => navigate('/consejos')}>Ver recomendaciones</PrimaryButton>
      <SecondaryButton to="/ecg">Cargar otro ECG</SecondaryButton>
    </>
  );
}

export function ProfilePage() {
  const user = getStoredUser();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    api.profile.get()
      .then((data) => { if (active) setProfile(data); })
      .catch((requestError) => {
        if (active && requestError.status !== 404) setError(getApiErrorMessage(requestError));
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const formData = fromProfilePayload(profile);
  return (
    <>
      <PageHeading title="Mi perfil" description="Consulte la información personal y cardiovascular asociada a su cuenta." />
      <SectionCard>
        <div className="tv-profile-avatar">{(user?.nombre || 'P').charAt(0).toUpperCase()}</div>
        <h2>{user?.nombre || 'Participante'}</h2>
        <p className="tv-muted">{user?.email || ''}</p>
        <div className="tv-profile-row"><span>Código de participante</span><strong>{user?.codigo_participante || '—'}</strong></div>
        <div className="tv-profile-row"><span>Edad</span><strong>{user?.edad ?? '—'}</strong></div>
        <div className="tv-profile-row"><span>Rol</span><strong>{user?.rol === 'PACIENTE' ? 'Paciente' : user?.rol || '—'}</strong></div>
      </SectionCard>
      {loading && <InfoNotice>Cargando perfil cardiovascular…</InfoNotice>}
      {error && <InfoNotice tone="danger">{error}</InfoNotice>}
      {!loading && !error && !profile && (
        <EmptyState title="Perfil cardiovascular pendiente" description="Todavía no se ha guardado el cuestionario de salud de esta cuenta." action={<SecondaryButton to="/perfil-inicial">Completar perfil cardiovascular</SecondaryButton>} />
      )}
      {profile && formData && (
        <SectionCard>
          <h2>Información cardiovascular</h2>
          <div className="tv-profile-row"><span>Peso</span><strong>{profile.peso_kg} kg</strong></div>
          <div className="tv-profile-row"><span>Estatura</span><strong>{profile.estatura_cm} cm</strong></div>
          <div className="tv-profile-row"><span>IMC calculado</span><strong>{profile.imc}</strong></div>
          <div className="tv-profile-row"><span>Presión arterial reportada</span><strong>{profile.presion_arterial}</strong></div>
          <div className="tv-profile-row"><span>Condiciones</span><strong>{formData.condiciones.join(', ')}</strong></div>
          <div className="tv-profile-row"><span>Medicamentos</span><strong>{formData.medicamentos}</strong></div>
          <div className="tv-profile-row"><span>Antecedentes familiares</span><strong>{formData.antecedentes}</strong></div>
          <div className="tv-profile-row"><span>Actividad semanal</span><strong>{formData.actividad}</strong></div>
          <div className="tv-profile-row"><span>Sueño promedio</span><strong>{formData.sueno}</strong></div>
          <div className="tv-profile-row"><span>Tabaquismo</span><strong>{formData.tabaquismo}</strong></div>
          <div className="tv-profile-row"><span>Alcohol</span><strong>{formData.alcohol}</strong></div>
          <SecondaryButton to="/perfil-inicial">Editar perfil cardiovascular</SecondaryButton>
        </SectionCard>
      )}
    </>
  );
}

export function EmergencyPage() {
  return (
    <div className="tv-emergency-screen">
      <div className="tv-emergency-card">
        <span className="tv-emergency-icon">!</span>
        <p className="tv-eyebrow">AVISO IMPORTANTE</p>
        <h1>Esto puede ser una emergencia</h1>
        <p className="tv-emergency-lead">Llame al 123 o acuda a urgencias ahora.</p>
        <p>Si presenta dolor o presión en el pecho, falta de aire repentina o desmayo, deje el cuestionario y pida ayuda de inmediato.</p>
        <a className="tv-button tv-button-danger" href="tel:123">Llamar al 123</a>
        <SecondaryButton to="/inicio">Volver al inicio</SecondaryButton>
      </div>
    </div>
  );
}

export function NotFoundPage() {
  return (
    <div className="tv-auth-screen"><div className="tv-auth-panel"><PageHeading title="No encontramos esta pantalla" description="La ruta solicitada no existe en este prototipo." /><SecondaryButton to="/">Volver al inicio de sesión</SecondaryButton></div></div>
  );
}
