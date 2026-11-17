import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { PatientLayout, ProfessionalLayout } from './components/Shared';
import {
  ConsentPage,
  InitialProfilePage,
  LoginPage,
  RegisterPage,
} from './pages/OnboardingPages';

import {
  EcgProcessingPage,
  EcgResultPage,
  EcgUploadPage,
  EmergencyPage,
  HabitsPage,
  HistoryPage,
  HomePage,
  MorningSurveyPage,
  NightSurveyPage,
  NotFoundPage,
  ProfilePage,
  RecommendationsPage,
} from './pages/PatientPages';
import { ProfessionalCaseDetailPage, ProfessionalCasesPage } from './pages/ProfessionalPages';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Acceso y creación de cuenta: flujo previo al área del paciente. */}
        <Route path="/" element={<LoginPage />} />
        <Route path="/registro" element={<RegisterPage />} />
        <Route path="/consentimiento" element={<ConsentPage />} />
        <Route path="/perfil-inicial" element={<InitialProfilePage />} />
        <Route path="/urgencias" element={<EmergencyPage />} />

        {/* Área del paciente: la barra inferior contiene las cinco secciones del diseño. */}
        <Route element={<PatientLayout />}>
          <Route path="/inicio" element={<HomePage />} />
          <Route path="/habitos" element={<HabitsPage />} />
          <Route path="/habitos/manana" element={<MorningSurveyPage />} />
          <Route path="/habitos/noche" element={<NightSurveyPage />} />
          <Route path="/historial" element={<HistoryPage />} />
          <Route path="/consejos" element={<RecommendationsPage />} />
          <Route path="/ecg" element={<EcgUploadPage />} />
          <Route path="/ecg/procesando" element={<EcgProcessingPage />} />
          <Route path="/ecg/resultado" element={<EcgResultPage />} />
          <Route path="/perfil" element={<ProfilePage />} />
        </Route>

        {/* El panel profesional tiene navegación y distribución propias. */}
        <Route path="/profesional" element={<ProfessionalLayout />}>
          <Route index element={<Navigate to="/profesional/casos" replace />} />
          <Route path="casos" element={<ProfessionalCasesPage />} />
          <Route path="casos/:caseId" element={<ProfessionalCaseDetailPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
