// Traduce las etiquetas legibles de los formularios a los valores ChoiceField
// definidos en los modelos y serializers de Django. No calcula ni inventa datos.

const profileMaps = {
  condiciones: {
    'Hipertensión (presión alta)': 'hipertension',
    'Diabetes o azúcar alta': 'diabetes',
    'Colesterol o triglicéridos altos': 'colesterol_trigliceridos_altos',
    'Enfermedad del corazón o infarto previo': 'enfermedad_cardiaca_infarto_previo',
    Ninguna: 'ninguna',
  },
  medicamentos: {
    'Sí, todos los días': 'TODOS_DIAS',
    'Sí, pero a veces se me olvidan': 'A_VECES_OLVIDA',
    No: 'NO',
  },
  antecedentes: { Sí: 'SI', No: 'NO', 'No sé': 'NO_SE' },
  frutas: { '0 a 1': '0_1', '2 a 4': '2_4', '5 o más': '5_MAS' },
  sal: {
    'Casi nunca': 'CASI_NUNCA',
    'Algunas veces por semana': 'ALGUNAS_VECES',
    'Todos los días': 'TODOS_DIAS',
  },
  bebidas: {
    'Casi nunca': 'CASI_NUNCA',
    '1 a 3 veces por semana': '1_3_SEMANA',
    'Todos los días': 'TODOS_DIAS',
  },
  actividad: { 'Menos de 60': 'MENOS_60', 'Entre 60 y 149': '60_149', '150 o más': '150_MAS' },
  sentado: { 'Menos de 6': 'MENOS_6', '6 a 8': '6_8', 'Más de 8': 'MAS_8' },
  estres: {
    'Nunca o casi nunca': 'CASI_NUNCA',
    'Algunos días': 'ALGUNOS_DIAS',
    'Casi todos los días': 'CASI_TODOS',
  },
  tabaquismo: {
    'Nunca he fumado': 'NUNCA',
    'Lo dejé': 'LO_DEJE',
    'Sí, ocasionalmente': 'OCASIONAL',
    'Sí, todos los días': 'DIARIO',
  },
  alcohol: { Nunca: 'NUNCA', '1 a 2 veces': '1_2', '3 o más': '3_MAS' },
};

const reverseMap = (mapping) => Object.fromEntries(Object.entries(mapping).map(([label, value]) => [value, label]));
const profileReverseMaps = Object.fromEntries(Object.entries(profileMaps).map(([key, map]) => [key, reverseMap(map)]));

function requiredMapped(mapping, value, fieldLabel) {
  const mapped = mapping[value];
  if (!mapped) throw new Error(`Seleccione una respuesta válida para: ${fieldLabel}.`);
  return mapped;
}

export function toProfilePayload(data) {
  if (!data.condiciones.length || !data.sintomasAhora.length || !data.sintomasMes.length) {
    throw new Error('Complete las preguntas de condiciones y síntomas antes de guardar.');
  }

  return {
    peso_kg: Number(data.peso),
    estatura_cm: Number(data.estatura),
    presion_arterial: data.presion.trim(),
    condiciones_diagnosticadas: data.condiciones.map((value) => requiredMapped(profileMaps.condiciones, value, 'condiciones diagnosticadas')),
    toma_medicamentos: requiredMapped(profileMaps.medicamentos, data.medicamentos, 'medicamentos'),
    antecedentes_familiares: requiredMapped(profileMaps.antecedentes, data.antecedentes, 'antecedentes familiares'),
    frutas_verduras_dia: requiredMapped(profileMaps.frutas, data.frutas, 'frutas y verduras'),
    sal_procesados: requiredMapped(profileMaps.sal, data.sal, 'sal y procesados'),
    bebidas_azucaradas: requiredMapped(profileMaps.bebidas, data.bebidas, 'bebidas azucaradas'),
    actividad_min_semana: requiredMapped(profileMaps.actividad, data.actividad, 'actividad física'),
    horas_sentado: requiredMapped(profileMaps.sentado, data.sentado, 'horas sentado'),
    horas_sueno_promedio: requiredMapped(
      { 'Menos de 6': 'Menos de 6', 'Entre 6 y 7': 'Entre 6 y 7', 'Entre 7 y 9': 'Entre 7 y 9', 'Más de 9': 'Más de 9' },
      data.sueno,
      'horas de sueño',
    ),
    estres_dos_semanas: requiredMapped(profileMaps.estres, data.estres, 'estrés de las últimas dos semanas'),
    tabaquismo: requiredMapped(profileMaps.tabaquismo, data.tabaquismo, 'tabaquismo'),
    alcohol_semana: requiredMapped(profileMaps.alcohol, data.alcohol, 'consumo de alcohol'),
    sintomas_ahora: data.sintomasAhora,
    sintomas_ultimo_mes: data.sintomasMes,
    hora_despertar: data.despertar || null,
    hora_acostarse: data.acostarse || null,
  };
}

export function fromProfilePayload(profile) {
  if (!profile) return null;
  const mapArray = (values, mapping) => (values || []).map((value) => mapping[value] || value);
  return {
    peso: profile.peso_kg ?? '',
    estatura: profile.estatura_cm ?? '',
    presion: profile.presion_arterial ?? '',
    condiciones: mapArray(profile.condiciones_diagnosticadas, profileReverseMaps.condiciones),
    medicamentos: profileReverseMaps.medicamentos[profile.toma_medicamentos] || '',
    antecedentes: profileReverseMaps.antecedentes[profile.antecedentes_familiares] || '',
    frutas: profileReverseMaps.frutas[profile.frutas_verduras_dia] || '',
    sal: profileReverseMaps.sal[profile.sal_procesados] || '',
    bebidas: profileReverseMaps.bebidas[profile.bebidas_azucaradas] || '',
    actividad: profileReverseMaps.actividad[profile.actividad_min_semana] || '',
    sentado: profileReverseMaps.sentado[profile.horas_sentado] || '',
    sueno: profile.horas_sueno_promedio || '',
    estres: profileReverseMaps.estres[profile.estres_dos_semanas] || '',
    tabaquismo: profileReverseMaps.tabaquismo[profile.tabaquismo] || '',
    alcohol: profileReverseMaps.alcohol[profile.alcohol_semana] || '',
    sintomasAhora: profile.sintomas_ahora || [],
    sintomasMes: profile.sintomas_ultimo_mes || [],
    despertar: profile.hora_despertar?.slice(0, 5) || '',
    acostarse: profile.hora_acostarse?.slice(0, 5) || '',
  };
}

const morningMaps = {
  sleepHours: { 'Menos de 5': 'MENOS_5', '5–6': '5_6', '6–7': '6_7', '7–9': '7_9', 'Más de 9': 'MAS_9' },
  awakenings: { No: 'NINGUNO', '1 vez': 'UNA_VEZ', '2 o 3 veces': 'DOS_TRES', 'Muchas veces': 'MUCHAS' },
  bathroom: { No: 'NINGUNA', '1 vez': 'UNA', '2 o más veces': 'DOS_MAS' },
  feeling: { 'Descansado(a)': 'DESCANSADO', 'Más o menos': 'REGULAR', 'Cansado(a)': 'CANSADO' },
  bedtime: {
    'Antes de las 10 p. m.': 'ANTES_22',
    '10–11 p. m.': '22_23',
    '11 p. m.–12 a. m.': '23_00',
    'Después de las 12': 'DESPUES_00',
  },
};

export function toMorningPayload(answers) {
  const payload = {
    horas_sueno_anoche: requiredMapped(morningMaps.sleepHours, answers.sleepHours, 'horas de sueño'),
    despertares_noche: requiredMapped(morningMaps.awakenings, answers.awakenings, 'despertares nocturnos'),
    idas_bano_noche: requiredMapped(morningMaps.bathroom, answers.bathroom, 'idas al baño'),
    sensacion_despertar: requiredMapped(morningMaps.feeling, answers.feeling, 'sensación al despertar'),
  };
  if (answers.bedtime) payload.hora_acostarse_anoche = requiredMapped(morningMaps.bedtime, answers.bedtime, 'hora de acostarse');
  return payload;
}

const nightMaps = {
  nap: { No: 'NO', 'Menos de 30 min': 'MENOS_30', '30 a 60 min': '30_60', 'Más de 1 hora': 'MAS_60' },
  walk: { No: 'NO', '10–20 min': '10_20', '20–30 min': '20_30', 'Más de 30 min': 'MAS_30' },
  exercise: { No: 'NO', 'Sí, suave (yoga, estiramiento)': 'SUAVE', 'Sí, moderado (bici, baile, trotar)': 'MODERADO', 'Sí, intenso': 'INTENSO' },
  fruit: { '0': '0', '1–2': '1_2', '3–4': '3_4', '5 o más': '5_MAS' },
  processed: { No: 'NO', 'Una vez': 'UNA', 'Varias veces': 'VARIAS' },
  sugary: { No: 'NO', '1 vaso': 'UN_VASO', '2 o más': 'DOS_MAS' },
  water: { '0–2': '0_2', '3–5': '3_5', '6–8': '6_8', 'Más de 8': 'MAS_8' },
  salt: { No: 'NO', 'Un poco': 'UN_POCO', 'Sí, bastante': 'BASTANTE' },
  stress: { Bajo: 'BAJO', Medio: 'MEDIO', Alto: 'ALTO' },
  smoked: { No: 'NO', '1–5 cigarrillos': '1_5', 'Más de 5': 'MAS_5' },
  alcohol: { No: 'NO', '1–2 tragos': '1_2', '3 o más': '3_MAS' },
  medication: { Sí: 'SI', 'Se me olvidó': 'OLVIDO' },
};

export function toNightPayload(answers, profile = null) {
  const payload = {
    siesta_tarde: requiredMapped(nightMaps.nap, answers.nap, 'siesta'),
    caminata_hoy: requiredMapped(nightMaps.walk, answers.walk, 'caminata'),
    ejercicio_hoy: requiredMapped(nightMaps.exercise, answers.exercise, 'ejercicio'),
    sentado_mas_6h: answers.sitting === 'Sí',
    frutas_verduras_hoy: requiredMapped(nightMaps.fruit, answers.fruit, 'frutas y verduras'),
    fritos_paquete_hoy: requiredMapped(nightMaps.processed, answers.processed, 'comida procesada'),
    bebida_azucarada_hoy: requiredMapped(nightMaps.sugary, answers.sugary, 'bebidas azucaradas'),
    vasos_agua_respuesta: requiredMapped(nightMaps.water, answers.water, 'vasos de agua'),
    sal_extra_hoy: requiredMapped(nightMaps.salt, answers.salt, 'sal adicional'),
    estres_hoy: requiredMapped(nightMaps.stress, answers.stress, 'estrés'),
    sintoma_hoy: answers.symptom === 'Sí',
  };

  if (profile && ['OCASIONAL', 'DIARIO'].includes(profile.tabaquismo)) {
    payload.fumo_hoy = requiredMapped(nightMaps.smoked, answers.smoked, 'consumo de tabaco hoy');
  }
  if (profile && profile.alcohol_semana && profile.alcohol_semana !== 'NUNCA') {
    payload.alcohol_hoy = requiredMapped(nightMaps.alcohol, answers.alcohol, 'consumo de alcohol hoy');
  }
  if (profile && profile.toma_medicamentos && profile.toma_medicamentos !== 'NO') {
    payload.medicamentos_hoy = requiredMapped(nightMaps.medication, answers.medication, 'medicamentos de hoy');
  }

  return payload;
}

const historyDisplay = {
  horas_sueno_anoche: { MENOS_5: 'Menos de 5 horas', '5_6': '5–6 horas', '6_7': '6–7 horas', '7_9': '7–9 horas', MAS_9: 'Más de 9 horas' },
  despertares_noche: { NINGUNO: 'No', UNA_VEZ: '1 vez', DOS_TRES: '2 o 3 veces', MUCHAS: 'Muchas veces' },
  idas_bano_noche: { NINGUNA: 'No', UNA: '1 vez', DOS_MAS: '2 o más veces' },
  sensacion_despertar: { DESCANSADO: 'Descansado(a)', REGULAR: 'Más o menos', CANSADO: 'Cansado(a)' },
  hora_acostarse_anoche: { ANTES_22: 'Antes de las 10 p. m.', '22_23': '10–11 p. m.', '23_00': '11 p. m.–12 a. m.', DESPUES_00: 'Después de las 12' },
  siesta_tarde: { NO: 'No', MENOS_30: 'Menos de 30 min', '30_60': '30 a 60 min', MAS_60: 'Más de 1 hora' },
  caminata_hoy: { NO: 'No', '10_20': '10–20 min', '20_30': '20–30 min', MAS_30: 'Más de 30 min' },
  ejercicio_hoy: { NO: 'No', SUAVE: 'Suave', MODERADO: 'Moderado', INTENSO: 'Intenso' },
  frutas_verduras_hoy: { '0': '0', '1_2': '1–2', '3_4': '3–4', '5_MAS': '5 o más' },
  fritos_paquete_hoy: { NO: 'No', UNA: 'Una vez', VARIAS: 'Varias veces' },
  bebida_azucarada_hoy: { NO: 'No', UN_VASO: '1 vaso', DOS_MAS: '2 o más' },
  vasos_agua_respuesta: { '0_2': '0–2 vasos', '3_5': '3–5 vasos', '6_8': '6–8 vasos', MAS_8: 'Más de 8 vasos' },
  sal_extra_hoy: { NO: 'No', UN_POCO: 'Un poco', BASTANTE: 'Sí, bastante' },
  estres_hoy: { BAJO: 'Bajo', MEDIO: 'Medio', ALTO: 'Alto' },
  fumo_hoy: { NO: 'No', '1_5': '1–5 cigarrillos', MAS_5: 'Más de 5' },
  alcohol_hoy: { NO: 'No', '1_2': '1–2 tragos', '3_MAS': '3 o más' },
  medicamentos_hoy: { SI: 'Sí', OLVIDO: 'Se me olvidó' },
};

export function displayHistoryValue(field, value) {
  if (value === null || value === undefined || value === '') return null;
  return historyDisplay[field]?.[value] ?? String(value);
}

export const historyCategoryValues = {
  Todas: '',
  Sueño: 'sueno',
  'Actividad física': 'actividad_fisica',
  'Alimentación e hidratación': 'alimentacion_hidratacion',
  'Estrés y bienestar': 'estres_bienestar',
  'Tabaco, alcohol y medicamentos': 'tabaco_alcohol_medicamentos',
};

export function toClarityCode(label) {
  const values = { Sí: 'SI', 'Más o menos': 'MAS_O_MENOS', No: 'NO' };
  return requiredMapped(values, label, 'claridad de la recomendación');
}

export function fromClarityCode(value) {
  return ({ SI: 'Sí', MAS_O_MENOS: 'Más o menos', NO: 'No' })[value] || '';
}

export function displayRecommendationCategory(value) {
  return ({
    ALIMENTACION: 'Alimentación',
    HIDRATACION: 'Hidratación',
    ACTIVIDAD_FISICA: 'Actividad física',
    SUENO: 'Sueño',
    ESTRES: 'Estrés',
    TABAQUISMO: 'Tabaquismo',
  })[value] || value || 'Recomendación';
}
