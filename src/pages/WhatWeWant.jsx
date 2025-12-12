import { CheckCircle, Target, Scale, Shield } from 'lucide-react';
import { Card } from '@/components/ui/card';

const WhatWeWant = () => {
  const goals = [
    {
      icon: <Scale className="h-8 w-8 text-slate-600" />,
      title: "Enhanced Police Accountability",
      description: "Clear, consistent policies for documenting and reviewing police conduct during public demonstrations.",
      details: [
        "Body-worn camera footage availability for public interest cases",
        "Public reporting of use-of-force incidents at demonstrations",
        "Independent oversight of public order policing tactics",
        "Regular review of protest policing protocols"
      ]
    },
    {
      icon: <Shield className="h-8 w-8 text-slate-600" />,
      title: "Protection of Civil Liberties",
      description: "Safeguarding the rights to free expression and peaceful assembly under UK law.",
      details: [
        "Clear guidelines protecting peaceful demonstrators",
        "Officer training on protest rights under the Human Rights Act",
        "Protection for journalists and legal observers at demonstrations",
        "Proportionate policing responses to peaceful assembly"
      ]
    },
    {
      icon: <Target className="h-8 w-8 text-slate-600" />,
      title: "Transparent Documentation",
      description: "Public access to information about police activities during demonstrations.",
      details: [
        "Proactive disclosure of protest-related incidents",
        "Accessible records of public order deployments",
        "Clear identification of officers at demonstrations",
        "Regular public reporting on protest policing outcomes"
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">
              Our Goals
            </h1>
            <p className="text-xl text-slate-600 max-w-3xl mx-auto">
              Our vision for transparent, accountable public order policing that respects civil liberties.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Introduction */}
        <div className="max-w-4xl mx-auto text-center mb-16">
          <p className="text-lg text-slate-700 leading-relaxed">
            We advocate for improved transparency and accountability in public order policing.
            Our goals are rooted in democratic principles and the belief that transparency
            strengthens public trust in policing.
          </p>
        </div>

        {/* Goals Grid */}
        <div className="space-y-12">
          {goals.map((goal, index) => (
            <Card key={index} className="p-8 border border-slate-200">
              <div className="flex flex-col lg:flex-row gap-8">
                <div className="flex-shrink-0">
                  <div className="flex items-center justify-center w-16 h-16 bg-slate-100 rounded-lg">
                    {goal.icon}
                  </div>
                </div>

                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-slate-900 mb-4">{goal.title}</h2>
                  <p className="text-lg text-slate-700 mb-6">{goal.description}</p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {goal.details.map((detail, detailIndex) => (
                      <div key={detailIndex} className="flex items-start gap-3">
                        <CheckCircle className="h-5 w-5 text-slate-500 mt-0.5 flex-shrink-0" />
                        <span className="text-slate-700">{detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Implementation Section */}
        <div className="mt-16 bg-white rounded-lg p-8 border border-slate-200">
          <h2 className="text-2xl font-bold text-slate-900 mb-6 text-center">How We Work</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-12 h-12 bg-slate-900 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                1
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Documentation</h3>
              <p className="text-slate-600">
                Collecting and verifying publicly available evidence from demonstrations.
              </p>
            </div>

            <div className="text-center">
              <div className="w-12 h-12 bg-slate-900 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                2
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Analysis</h3>
              <p className="text-slate-600">
                Building a searchable database of police officers and their documented activities.
              </p>
            </div>

            <div className="text-center">
              <div className="w-12 h-12 bg-slate-900 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                3
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Transparency</h3>
              <p className="text-slate-600">
                Making information publicly accessible to support accountability.
              </p>
            </div>
          </div>
        </div>

        {/* Call to Action */}
        <div className="mt-16 text-center bg-slate-100 rounded-lg p-8">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Support Transparency</h2>
          <p className="text-slate-700 mb-6 max-w-2xl mx-auto">
            Help build a comprehensive public record. Your documented evidence contributes
            to transparency and accountability in public order policing.
          </p>
          <p className="text-sm text-slate-600">
            All operations comply with UK law. Data is collected exclusively from
            publicly available sources.
          </p>
        </div>
      </div>
    </div>
  );
};

export default WhatWeWant;

