import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { useEffect } from "react";
import Index from "./pages/Index";
import PatientDetail from "./pages/PatientDetail";
import ResearchDetail from "./pages/ResearchDetail";
import WearablesDetail from "./pages/WearablesDetail";
import SentimentDetail from "./pages/SentimentDetail";
import NotesDetail from "./pages/NotesDetail";
import PatientSummary from "./pages/PatientSummary";
import Calendar from "./pages/Calendar";
import Messages from "./pages/Messages";
import PreVisitQuestionnaire from "./pages/PreVisitQuestionnaire";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

function RouteLogger() {
  const location = useLocation();

  useEffect(() => {
    if (import.meta.env.DEV) {
      console.log("[route]", location.pathname, { search: location.search });
    }
  }, [location.pathname, location.search]);

  return null;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <RouteLogger />
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/messages" element={<Messages />} />
          <Route path="/patient/:id" element={<PatientDetail />} />
          <Route path="/patient/:id/summary" element={<PatientSummary />} />
          <Route path="/patient/:id/research" element={<ResearchDetail />} />
          <Route path="/patient/:id/wearables" element={<WearablesDetail />} />
          <Route path="/patient/:id/sentiment" element={<SentimentDetail />} />
          <Route path="/patient/:id/notes" element={<NotesDetail />} />
          <Route path="/patient/:id/questionnaires/pre-visit" element={<PreVisitQuestionnaire />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
