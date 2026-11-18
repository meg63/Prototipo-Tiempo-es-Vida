"""Banco oficial de 30 recomendaciones de Tiempo es Vida.

Transcripción del documento funcional, páginas 31 a 33.
No editar los textos sin versionar/validar el banco con el equipo.
"""

RECOMMENDATIONS = [
    {
        "codigo": "AL-01",
        "categoria": "ALIMENTACION",
        "situacion_identificada": "Pocas frutas y verduras (promedio de 7 días menor a 3 porciones)",
        "texto_recomendacion": "Intente sumar una porción de fruta o verdura a una de sus comidas hoy. La referencia es llegar a unas 5 porciones al día.",
    },
    {
        "codigo": "AL-02",
        "categoria": "ALIMENTACION",
        "situacion_identificada": "Poca variedad o poco acceso a fruta fresca",
        "texto_recomendacion": "Las frutas y verduras frescas, congeladas o enlatadas sin azúcar ni sal añadidas también sirven.",
    },
    {
        "codigo": "AL-03",
        "categoria": "ALIMENTACION",
        "situacion_identificada": "Consumo frecuente de ultraprocesados o comidas saladas",
        "texto_recomendacion": "Los embutidos, la comida rápida y los empacados suelen concentrar la sal. Pruebe reemplazar uno hoy por una preparación casera y use menos sal al cocinar y en la mesa.",
    },
    {
        "codigo": "AL-04",
        "categoria": "ALIMENTACION",
        "situacion_identificada": "Bebidas azucaradas frecuentes",
        "texto_recomendacion": "Pruebe cambiar una bebida azucarada por agua o una infusión sin azúcar. Los jugos, incluso sin azúcar añadida, aportan azúcares libres.",
    },
    {
        "codigo": "AL-05",
        "categoria": "ALIMENTACION",
        "situacion_identificada": "Interés en mejorar su patrón general",
        "texto_recomendacion": "Cuando pueda, elija cereales integrales en lugar de refinados (avena, arroz o pan integral).",
    },
    {
        "codigo": "HI-01",
        "categoria": "HIDRATACION",
        "situacion_identificada": "Pocos vasos registrados varios días",
        "texto_recomendacion": "Tenga agua a la vista y tome pequeñas cantidades a lo largo del día, en lugar de mucha de una sola vez.",
    },
    {
        "codigo": "HI-02",
        "categoria": "HIDRATACION",
        "situacion_identificada": "Día caluroso o ejercicio registrado",
        "texto_recomendacion": "Con calor o ejercicio sus necesidades de líquido aumentan. Ajuste lo que toma.",
    },
    {
        "codigo": "HI-03",
        "categoria": "HIDRATACION",
        "situacion_identificada": "Pocos vasos y pocas porciones de fruta o verdura",
        "texto_recomendacion": "Las frutas y verduras también aportan agua; sumarlas ayuda a su hidratación.",
    },
    {
        "codigo": "HI-04",
        "categoria": "HIDRATACION",
        "situacion_identificada": "Quiere crear el hábito",
        "texto_recomendacion": "Un vaso de agua al despertar y otro con cada comida puede ser un ancla fácil.",
    },
    {
        "codigo": "HI-05",
        "categoria": "HIDRATACION",
        "situacion_identificada": "El usuario indica que su médico le limitó los líquidos",
        "texto_recomendacion": "Siga el límite que le indicó su equipo médico. La app no le mostrará metas de agua.",
    },
    {
        "codigo": "AF-01",
        "categoria": "ACTIVIDAD_FISICA",
        "situacion_identificada": "Menos de 60 min de actividad en 7 días",
        "texto_recomendacion": "Si su condición física lo permite, empiece con caminatas de 10 minutos. Cualquier cantidad de actividad es mejor que ninguna.",
    },
    {
        "codigo": "AF-02",
        "categoria": "ACTIVIDAD_FISICA",
        "situacion_identificada": "Entre 60 y 149 min en 7 días",
        "texto_recomendacion": "Va por buen camino: sume 10 a 15 minutos por semana hasta acercarse a 150 minutos de actividad moderada.",
    },
    {
        "codigo": "AF-03",
        "categoria": "ACTIVIDAD_FISICA",
        "situacion_identificada": "Sin fortalecimiento muscular en 7 días",
        "texto_recomendacion": "Incluya ejercicios de fuerza (sentadillas, bandas elásticas, subir escaleras) al menos 2 días por semana.",
    },
    {
        "codigo": "AF-04",
        "categoria": "ACTIVIDAD_FISICA",
        "situacion_identificada": "Muchas horas sentado",
        "texto_recomendacion": "Levántese y muévase unos minutos con frecuencia. Cambiar tiempo sentado por actividad, aunque sea ligera, aporta beneficios.",
    },
    {
        "codigo": "AF-05",
        "categoria": "ACTIVIDAD_FISICA",
        "situacion_identificada": "150 min o más en 7 días",
        "texto_recomendacion": "Alcanzó el mínimo semanal. Mantenga la constancia: más actividad, hasta unos 300 minutos, aporta beneficios adicionales.",
    },
    {
        "codigo": "SU-01",
        "categoria": "SUENO",
        "situacion_identificada": "Promedio de sueño menor a 7 h en 7 días",
        "texto_recomendacion": "Intente acostarse 15 a 30 minutos antes esta semana. La referencia para adultos es dormir 7 horas o más.",
    },
    {
        "codigo": "SU-02",
        "categoria": "SUENO",
        "situacion_identificada": "Horarios de dormir muy variables",
        "texto_recomendacion": "Procure acostarse y levantarse a horas parecidas, también los fines de semana.",
    },
    {
        "codigo": "SU-03",
        "categoria": "SUENO",
        "situacion_identificada": "Dificultad para dormir al menos 3 noches por semana",
        "texto_recomendacion": "Use la cama solo para dormir, reduzca pantallas y cafeína hacia la noche y mantenga el cuarto oscuro y fresco.",
    },
    {
        "codigo": "SU-04",
        "categoria": "SUENO",
        "situacion_identificada": "Dificultad para dormir al menos 3 noches por semana durante 3 meses o más",
        "texto_recomendacion": "Hable con su médico: el tratamiento inicial recomendado para el insomnio crónico es la terapia cognitivo-conductual, que también existe en formato telefónico o web.",
    },
    {
        "codigo": "SU-05",
        "categoria": "SUENO",
        "situacion_identificada": "Ronquidos fuertes, pausas al respirar o mucho sueño diurno",
        "texto_recomendacion": "Consulte a su médico: puede tratarse de un trastorno del sueño, como la apnea, que tiene tratamiento.",
    },
    {
        "codigo": "ES-01",
        "categoria": "ESTRES",
        "situacion_identificada": "Estrés de 4 o 5 en al menos 3 de 7 días",
        "texto_recomendacion": "Haga una pausa de 5 minutos: respire lento y profundo, suelte los hombros y aléjese de las pantallas.",
    },
    {
        "codigo": "ES-02",
        "categoria": "ESTRES",
        "situacion_identificada": "PSS-4 en rango alto o estrés de 4 o 5 en al menos 5 de 7 días",
        "texto_recomendacion": "El estrés sostenido se asocia con mayor riesgo cardiovascular. Considere hablar con un profesional de salud o de salud mental.",
    },
    {
        "codigo": "ES-03",
        "categoria": "ESTRES",
        "situacion_identificada": "Estrés alto y poca actividad",
        "texto_recomendacion": "Una caminata corta puede ayudarle a bajar la tensión; la actividad física también favorece la salud mental.",
    },
    {
        "codigo": "ES-04",
        "categoria": "ESTRES",
        "situacion_identificada": "Estrés alto persistente y poco contacto social",
        "texto_recomendacion": "Dedique unos minutos a conversar con alguien de confianza. Las relaciones de apoyo se asocian con mejor salud psicológica.",
    },
    {
        "codigo": "ES-05",
        "categoria": "ESTRES",
        "situacion_identificada": "Estrés moderado e interés en bienestar",
        "texto_recomendacion": "Anote hoy una cosa por la que se sienta agradecido/a. Optimismo, gratitud y propósito se asocian con menor riesgo cardiovascular, aunque la evidencia es observacional.",
    },
    {
        "codigo": "TA-01",
        "categoria": "TABAQUISMO",
        "situacion_identificada": "Fuma",
        "texto_recomendacion": "Dejar de fumar es una de las mejores decisiones para su corazón. Considere buscar apoyo profesional para dejarlo.",
    },
    {
        "codigo": "TA-02",
        "categoria": "TABAQUISMO",
        "situacion_identificada": "Fuma de 1 a 5 cigarrillos al día, o dice que «ya fuma poco»",
        "texto_recomendacion": "Incluso un cigarrillo al día conlleva un riesgo cardiovascular cercano a la mitad del de fumar 20. Reducir ayuda menos que dejarlo por completo.",
    },
    {
        "codigo": "TA-03",
        "categoria": "TABAQUISMO",
        "situacion_identificada": "Quiere dejar de fumar",
        "texto_recomendacion": "Combinar apoyo conductual (individual, grupal o telefónico) con un tratamiento indicado por un profesional aumenta sus probabilidades de éxito. Pregunte a su médico qué opciones hay para usted.",
    },
    {
        "codigo": "TA-04",
        "categoria": "TABAQUISMO",
        "situacion_identificada": "Usa vapeador u otros productos de tabaco",
        "texto_recomendacion": "La guía de la OMS para dejar el tabaco cubre cigarrillos, narguile, tabaco sin humo, puros y productos de tabaco calentado. Si usa alguno, también puede pedir apoyo para dejarlo.",
    },
    {
        "codigo": "TA-05",
        "categoria": "TABAQUISMO",
        "situacion_identificada": "Exposición a humo ajeno o recaída",
        "texto_recomendacion": "Evite los ambientes con humo de tabaco. Si recayó, no es un fracaso: retome su plan y pida apoyo.",
    },
]

assert len(RECOMMENDATIONS) == 30
