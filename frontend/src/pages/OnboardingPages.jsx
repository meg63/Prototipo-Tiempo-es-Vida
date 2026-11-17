import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ChoiceField,
  InfoNotice,
  MultiChoiceField,
  PageHeading,
  PrimaryButton,
  SectionCard,
  SecondaryButton,
  SelectField,
  TextField,
} from '../components/Shared';
import { api, getApiErrorMessage } from '../services/api';
import { fromProfilePayload, toProfilePayload } from '../services/mappers';

function AuthFrame({ children, subtitle = 'Cuidar su corazón también es cuidar su tiempo.' }) {
  return (
    <div className="tv-auth-screen">
      <div className="tv-auth-panel">
        <div className="tv-auth-brand">
          <span className="tv-brand-symbol">♥</span>
          <strong>CuidaCor</strong>
          <small>TIEMPO ES VIDA</small>
        </div>
        <p className="tv-auth-subtitle">{subtitle}</p>
        {children}
        <p className="tv-auth-footnote">Orientación preventiva. No reemplaza una consulta médica.</p>
      </div>
    </div>
  );
}

async function destinationAfterPatientLogin() {
  try {
    await api.consent.get();
  } catch (error) {
    if (error.status === 404) return '/consentimiento';
    throw error;
  }
  try {
    await api.profile.get();
    return '/inicio';
  } catch (error) {
    if (error.status === 404) return '/perfil-inicial';
    throw error;
  }
}

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await api.auth.login({ email: email.trim(), password });
      const user = response.usuario;
      if (user.rol === 'PROFESIONAL') {
        navigate('/profesional/casos', { replace: true });
      } else {
        navigate(await destinationAfterPatientLogin(), { replace: true });
      }
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthFrame subtitle="Su bienestar cardiovascular, un día a la vez.">
      <PageHeading title="Bienvenido(a)" description="Ingrese para continuar con su seguimiento." />
      <form className="tv-form" onSubmit={handleSubmit}>
        <TextField label="Correo electrónico" name="login-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        <TextField label="Contraseña" name="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        {error && <InfoNotice tone="danger">{error}</InfoNotice>}
        <PrimaryButton type="submit" disabled={loading}>{loading ? 'Ingresando…' : 'Ingresar'}</PrimaryButton>
      </form>
      <div className="tv-auth-links">
        <span>¿Aún no tiene cuenta?</span> <Link to="/registro">Crear cuenta</Link>
      </div>
      <InfoNotice>El sistema abrirá el espacio correspondiente al rol autorizado de su cuenta.</InfoNotice>
    </AuthFrame>
  );
}

export function RegisterPage() {
  const navigate = useNavigate();
  const [data, setData] = useState({ codigo: '', nombre: '', edad: '35', sexo: '', correo: '', contrasena: '', confirmar: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const update = (field) => (event) => setData((current) => ({ ...current, [field]: event.target.value }));

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    if (Number(data.edad) < 35 || Number(data.edad) > 99) {
      setError('El piloto está dirigido a personas de 35 a 99 años.');
      return;
    }
    if (data.contrasena.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }

    setLoading(true);
    try {
      await api.auth.register({
        email: data.correo.trim(),
        nombre: data.nombre.trim(),
        codigo_participante: data.codigo.trim(),
        edad: Number(data.edad),
        sexo: data.sexo,
        password: data.contrasena,
        password_confirmation: data.confirmar,
      });
      navigate('/consentimiento', { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthFrame subtitle="Piloto para personas de 35 años o más · Paso 1 de 3.">
      <PageHeading eyebrow="CREAR CUENTA" title="Registre sus datos" description="Use el código de participante que le entregó el equipo." />
      <form className="tv-form" onSubmit={handleSubmit}>
        <TextField label="Código de participante" name="codigo" value={data.codigo} onChange={update('codigo')} required placeholder="Código entregado por el equipo" />
        <TextField label="Nombre o alias" name="nombre" value={data.nombre} onChange={update('nombre')} required />
        <TextField label="Edad" name="edad" type="number" min="35" max="99" value={data.edad} onChange={update('edad')} required />
        <SelectField label="Sexo registrado (opcional)" name="sexo" value={data.sexo} onChange={update('sexo')} options={['Femenino', 'Masculino', 'Prefiero no decirlo']} />
        <TextField label="Correo electrónico" name="correo" type="email" value={data.correo} onChange={update('correo')} required />
        <TextField label="Contraseña" name="contrasena" type="password" value={data.contrasena} onChange={update('contrasena')} required helper="Mínimo 8 caracteres." autoComplete="new-password" />
        <TextField label="Confirme la contraseña" name="confirmar" type="password" value={data.confirmar} onChange={update('confirmar')} required autoComplete="new-password" />
        {error && <InfoNotice tone="danger">{error}</InfoNotice>}
        <PrimaryButton type="submit" disabled={loading}>{loading ? 'Creando cuenta…' : 'Continuar'}</PrimaryButton>
      </form>
      <div className="tv-auth-links"><span>¿Ya tiene cuenta?</span> <Link to="/">Ingresar</Link></div>
    </AuthFrame>
  );
}

export function ConsentPage() {
  const navigate = useNavigate();
  const [acceptData, setAcceptData] = useState(false);
  const [acceptPilot, setAcceptPilot] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleContinue() {
    setError('');
    if (!acceptData || !acceptPilot) {
      setError('Para continuar debe marcar las dos casillas de aceptación.');
      return;
    }
    setLoading(true);
    try {
      await api.consent.create({
        acepta_tratamiento_datos: acceptData,
        acepta_piloto_no_clinico: acceptPilot,
      });
      navigate('/perfil-inicial', { replace: true });
    } catch (requestError) {
      if (requestError.status === 409) {
        navigate('/perfil-inicial', { replace: true });
      } else {
        setError(getApiErrorMessage(requestError));
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleCancel() {
    try { await api.auth.logout(); } catch { /* La sesión local se limpia en api.auth.logout. */ }
    navigate('/', { replace: true });
  }

  return (
    <AuthFrame subtitle="Paso 2 de 3 · Consentimiento informado.">
      <PageHeading title="Antes de continuar" description="Lea la información del piloto y confirme su decisión." />
      <SectionCard>
        <p>Solo recogemos los datos necesarios para el piloto: su perfil, sus hábitos y los ECG de prueba. Se usan para evaluar la plataforma.</p>
        <InfoNotice tone="warning">Tiempo es vida entrega orientación, no un diagnóstico. Los resultados de ECG son experimentales y utilizan casos de prueba públicos de PTB-XL.</InfoNotice>
        <label className="tv-check-row tv-check-large"><input type="checkbox" checked={acceptData} onChange={(e) => setAcceptData(e.target.checked)} /><span>Autorizo el tratamiento de mis datos personales.</span></label>
        <label className="tv-check-row tv-check-large"><input type="checkbox" checked={acceptPilot} onChange={(e) => setAcceptPilot(e.target.checked)} /><span>Entiendo que es un piloto experimental y que no recibo un diagnóstico.</span></label>
        {error && <InfoNotice tone="danger">{error}</InfoNotice>}
        <PrimaryButton onClick={handleContinue} disabled={loading}>{loading ? 'Guardando…' : 'Aceptar y continuar'}</PrimaryButton>
        <SecondaryButton onClick={handleCancel}>Cancelar</SecondaryButton>
      </SectionCard>
    </AuthFrame>
  );
}

const conditionOptions = [
  'Hipertensión (presión alta)',
  'Diabetes o azúcar alta',
  'Colesterol o triglicéridos altos',
  'Enfermedad del corazón o infarto previo',
  'Ninguna',
];
const urgentSymptoms = [
  'Dolor, presión u opresión en el pecho que dura más de unos minutos',
  'Dolor que se extiende al brazo, la mandíbula o la espalda',
  'Falta de aire de forma repentina',
  'Desmayo o mareo fuerte',
  'Ninguno',
];
const lastMonthSymptoms = [
  'Palpitaciones o latidos irregulares',
  'Cansancio o falta de aire al hacer esfuerzos que antes no te costaban',
  'Hinchazón en los tobillos o las piernas',
  'Ninguno',
];

const emptyProfile = {
  peso: '', estatura: '', presion: '', condiciones: [], medicamentos: '', antecedentes: '',
  frutas: '', sal: '', bebidas: '', actividad: '', sentado: '', sueno: '', estres: '',
  tabaquismo: '', alcohol: '', sintomasAhora: [], sintomasMes: [], despertar: '', acostarse: '',
};

export function InitialProfilePage() {
  const navigate = useNavigate();
  const [data, setData] = useState(emptyProfile);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const update = (field) => (event) => setData((current) => ({ ...current, [field]: event.target.value }));
  const updateMulti = (field) => (value) => setData((current) => ({ ...current, [field]: value }));
  const heightInMeters = Number(data.estatura) / 100;
  const bmi = data.peso && heightInMeters > 0 ? (Number(data.peso) / (heightInMeters * heightInMeters)).toFixed(1) : '';

  useEffect(() => {
    let active = true;
    api.profile.get()
      .then((profile) => { if (active) setData(fromProfilePayload(profile) || emptyProfile); })
      .catch((requestError) => {
        // 404 es normal cuando la persona acaba de aceptar el consentimiento.
        if (active && requestError.status !== 404) setError(getApiErrorMessage(requestError));
      })
      .finally(() => { if (active) setLoadingProfile(false); });
    return () => { active = false; };
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    if (!data.peso || !data.estatura || !data.presion || !data.medicamentos || !data.antecedentes ||
        !data.frutas || !data.sal || !data.bebidas || !data.actividad || !data.sentado || !data.sueno ||
        !data.estres || !data.tabaquismo || !data.alcohol) {
      setError('Complete todos los campos obligatorios del perfil cardiovascular.');
      return;
    }
    if (data.condiciones.length === 0 || data.sintomasAhora.length === 0 || data.sintomasMes.length === 0) {
      setError('Seleccione al menos una opción en condiciones y síntomas.');
      return;
    }
    if (data.sintomasAhora.includes('Ninguno') && data.sintomasAhora.length > 1) {
      setError('La opción «Ninguno» no se puede combinar con otros síntomas actuales.');
      return;
    }

    setLoading(true);
    try {
      await api.profile.save(toProfilePayload(data));
      if (data.sintomasAhora.some((item) => item !== 'Ninguno')) {
        navigate('/urgencias', { replace: true });
      } else {
        navigate('/inicio', { replace: true });
      }
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="tv-onboarding-screen">
      <div className="tv-onboarding-content">
        <div className="tv-onboarding-brand"><span className="tv-brand-symbol">♥</span><strong>CuidaCor</strong><small>PASO 3 DE 3</small></div>
        <PageHeading title="Su perfil cardiovascular" description="La plataforma orienta, no diagnostica. Complete los datos que le solicitamos." />
        {loadingProfile && <InfoNotice>Cargando información del perfil…</InfoNotice>}
        <form className="tv-form" onSubmit={handleSubmit}>
          <SectionCard>
            <h2>Datos de salud</h2>
            <div className="tv-form-grid">
              <TextField label="Peso (kg)" name="peso" type="number" min="30" max="250" step="0.1" value={data.peso} onChange={update('peso')} required />
              <TextField label="Estatura (cm)" name="estatura" type="number" min="120" max="220" value={data.estatura} onChange={update('estatura')} required />
            </div>
            {bmi && <div className="tv-bmi-preview"><span>IMC calculado automáticamente</span><strong>{bmi}</strong></div>}
            <TextField label="Presión arterial más reciente" name="presion" value={data.presion} onChange={update('presion')} required placeholder="Ej. 130/85 o No sé" />
            <MultiChoiceField label="¿Un médico le ha dicho que tiene alguna de estas condiciones?" options={conditionOptions} value={data.condiciones} onChange={updateMulti('condiciones')} />
            <ChoiceField label="¿Toma medicamentos para alguna de esas condiciones?" name="medicamentos" value={data.medicamentos} onChange={(value) => setData((c) => ({ ...c, medicamentos: value }))} options={['Sí, todos los días', 'Sí, pero a veces se me olvidan', 'No']} />
            <ChoiceField label="¿Su papá, mamá o hermanos tuvieron infarto, enfermedad del corazón o derrame cerebral antes de los 60 años?" name="antecedentes" value={data.antecedentes} onChange={(value) => setData((c) => ({ ...c, antecedentes: value }))} options={['Sí', 'No', 'No sé']} />
          </SectionCard>

          <SectionCard>
            <h2>Hábitos</h2>
            <ChoiceField label="¿Cuántas porciones de frutas y verduras come al día?" name="frutas" value={data.frutas} onChange={(value) => setData((c) => ({ ...c, frutas: value }))} options={['0 a 1', '2 a 4', '5 o más']} />
            <ChoiceField label="¿Agrega sal a la comida servida o consume embutidos, enlatados o paquetes con frecuencia?" name="sal" value={data.sal} onChange={(value) => setData((c) => ({ ...c, sal: value }))} options={['Casi nunca', 'Algunas veces por semana', 'Todos los días']} />
            <ChoiceField label="¿Con qué frecuencia toma gaseosas, jugos de caja o bebidas azucaradas?" name="bebidas" value={data.bebidas} onChange={(value) => setData((c) => ({ ...c, bebidas: value }))} options={['Casi nunca', '1 a 3 veces por semana', 'Todos los días']} />
            <ChoiceField label="¿Cuántos minutos a la semana hace actividad física moderada?" name="actividad" value={data.actividad} onChange={(value) => setData((c) => ({ ...c, actividad: value }))} options={['Menos de 60', 'Entre 60 y 149', '150 o más']} />
            <ChoiceField label="¿Cuántas horas al día pasa sentado(a)?" name="sentado" value={data.sentado} onChange={(value) => setData((c) => ({ ...c, sentado: value }))} options={['Menos de 6', '6 a 8', 'Más de 8']} />
            <ChoiceField label="¿Cuántas horas duerme por noche, en promedio?" name="sueno" value={data.sueno} onChange={(value) => setData((c) => ({ ...c, sueno: value }))} options={['Menos de 6', 'Entre 6 y 7', 'Entre 7 y 9', 'Más de 9']} />
            <ChoiceField label="En las últimas dos semanas, ¿qué tan seguido se ha sentido estresado(a), nervioso(a) o agobiado(a)?" name="estres" value={data.estres} onChange={(value) => setData((c) => ({ ...c, estres: value }))} options={['Nunca o casi nunca', 'Algunos días', 'Casi todos los días']} />
            <ChoiceField label="¿Fuma cigarrillo o vapeador?" name="tabaquismo" value={data.tabaquismo} onChange={(value) => setData((c) => ({ ...c, tabaquismo: value }))} options={['Nunca he fumado', 'Lo dejé', 'Sí, ocasionalmente', 'Sí, todos los días']} />
            <ChoiceField label="¿Cuántas veces a la semana toma bebidas alcohólicas?" name="alcohol" value={data.alcohol} onChange={(value) => setData((c) => ({ ...c, alcohol: value }))} options={['Nunca', '1 a 2 veces', '3 o más']} />
          </SectionCard>

          <SectionCard>
            <h2>Síntomas y horario</h2>
            <InfoNotice tone="danger">Si presenta ahora dolor u opresión en el pecho, falta de aire repentina o desmayo, deje el cuestionario y solicite ayuda de urgencias.</InfoNotice>
            <MultiChoiceField label="¿Tiene ahora alguno de estos síntomas?" options={urgentSymptoms} value={data.sintomasAhora} onChange={updateMulti('sintomasAhora')} />
            <MultiChoiceField label="En el último mes, ¿ha sentido alguno de estos síntomas?" options={lastMonthSymptoms} value={data.sintomasMes} onChange={updateMulti('sintomasMes')} />
            <div className="tv-form-grid">
              <TextField label="Hora a la que se levanta" name="despertar" type="time" value={data.despertar} onChange={update('despertar')} />
              <TextField label="Hora a la que se acuesta" name="acostarse" type="time" value={data.acostarse} onChange={update('acostarse')} />
            </div>
            <small className="tv-field-helper">El horario permite orientar cuál encuesta diaria se muestra primero.</small>
          </SectionCard>
          {error && <InfoNotice tone="danger">{error}</InfoNotice>}
          <PrimaryButton type="submit" disabled={loading || loadingProfile}>{loading ? 'Guardando perfil…' : 'Guardar y continuar'}</PrimaryButton>
        </form>
      </div>
    </div>
  );
}
