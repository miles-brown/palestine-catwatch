import { Users, Scale, Eye } from 'lucide-react';
import { Card } from '@/components/ui/card';

const OurStory = () => {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">
              Our Mission
            </h1>
            <p className="text-xl text-slate-600 max-w-3xl mx-auto">
              Promoting transparency and accountability in public order policing through evidence-based documentation.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Introduction */}
        <div className="prose prose-lg max-w-none mb-12">
          <p className="text-lg text-slate-700 leading-relaxed mb-6">
            The Palestine Accountability Campaign is an independent research initiative dedicated to
            documenting police conduct at public demonstrations in the UK. We believe that transparency
            and systematic documentation serve the public interest and strengthen democratic accountability.
          </p>

          <p className="text-lg text-slate-700 leading-relaxed mb-6">
            Our work began during the Palestine solidarity protests, where we identified the need for
            comprehensive, evidence-based records of public order policing. Our database serves
            researchers, journalists, and the public seeking factual information about police
            activities at demonstrations.
          </p>
        </div>

        {/* Values Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          <Card className="p-6 text-center border border-slate-200">
            <Eye className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-slate-900 mb-3">Transparency</h3>
            <p className="text-slate-600">
              Open, factual documentation from publicly available sources with full attribution.
            </p>
          </Card>

          <Card className="p-6 text-center border border-slate-200">
            <Users className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-slate-900 mb-3">Accountability</h3>
            <p className="text-slate-600">
              Supporting the public interest in oversight of police conduct at public demonstrations.
            </p>
          </Card>

          <Card className="p-6 text-center border border-slate-200">
            <Scale className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-slate-900 mb-3">Objectivity</h3>
            <p className="text-slate-600">
              Evidence-based documentation focused on verifiable facts rather than commentary.
            </p>
          </Card>
        </div>

        {/* Our Approach */}
        <div className="bg-white rounded-lg p-8 border border-slate-200 mb-12">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">Our Approach</h2>
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-2 h-2 bg-slate-600 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-slate-700">
                <strong>Evidence-Based Documentation:</strong> We rely exclusively on publicly available
                materials including videos, photographs, social media posts, and news reports.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-2 h-2 bg-slate-600 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-slate-700">
                <strong>Factual Reporting:</strong> Our documentation focuses on observable actions and
                verifiable information, avoiding speculation or inflammatory language.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-2 h-2 bg-slate-600 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-slate-700">
                <strong>Source Transparency:</strong> Every piece of information is linked to its original
                source, allowing visitors to verify and examine the evidence themselves.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-2 h-2 bg-slate-600 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-slate-700">
                <strong>Legal Compliance:</strong> All operations comply with UK data protection law
                and serve the legitimate public interest in police accountability.
              </p>
            </div>
          </div>
        </div>

        {/* Call to Action */}
        <div className="text-center bg-slate-100 rounded-lg p-8">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Contribute to the Record</h2>
          <p className="text-slate-700 mb-6">
            Help build a comprehensive public record of police conduct at demonstrations.
            Your documented evidence contributes to transparency and accountability.
          </p>
          <p className="text-sm text-slate-600">
            All data is collected from publicly available sources in accordance with UK law.
          </p>
        </div>
      </div>
    </div>
  );
};

export default OurStory;

