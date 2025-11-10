import { CheckCircle, Target, Scale, Shield } from 'lucide-react';
import { Card } from '@/components/ui/card';

const WhatWeWant = () => {
  const goals = [
    {
      icon: <Scale className="h-8 w-8 text-blue-600" />,
      title: "Enhanced Police Accountability",
      description: "Clear, consistent policies for documenting and reviewing police conduct during public demonstrations.",
      details: [
        "Mandatory body cameras during all protest interactions",
        "Public reporting of use-of-force incidents",
        "Independent oversight of protest policing tactics",
        "Regular community review of police protocols"
      ]
    },
    {
      icon: <Shield className="h-8 w-8 text-blue-600" />,
      title: "Protection of Constitutional Rights",
      description: "Safeguarding the fundamental rights to free speech, assembly, and peaceful protest.",
      details: [
        "Clear guidelines protecting peaceful protesters",
        "Training programs on constitutional rights for officers",
        "Prohibition of intimidation tactics against lawful assembly",
        "Protection for journalists and legal observers"
      ]
    },
    {
      icon: <Target className="h-8 w-8 text-blue-600" />,
      title: "Transparent Documentation",
      description: "Public access to information about police activities during demonstrations.",
      details: [
        "Proactive disclosure of protest-related incidents",
        "Public database of officer conduct records",
        "Community access to body camera footage",
        "Regular public reporting on protest policing"
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              What We Want
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Our vision for a more transparent, accountable, and rights-respecting approach to protest policing.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Introduction */}
        <div className="max-w-4xl mx-auto text-center mb-16">
          <p className="text-lg text-gray-700 leading-relaxed">
            We advocate for systemic changes that protect constitutional rights while ensuring 
            public safety. Our goals are rooted in democratic principles and the belief that 
            transparency strengthens both community trust and effective law enforcement.
          </p>
        </div>

        {/* Goals Grid */}
        <div className="space-y-12">
          {goals.map((goal, index) => (
            <Card key={index} className="p-8">
              <div className="flex flex-col lg:flex-row gap-8">
                <div className="flex-shrink-0">
                  <div className="flex items-center justify-center w-16 h-16 bg-blue-100 rounded-lg">
                    {goal.icon}
                  </div>
                </div>
                
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-900 mb-4">{goal.title}</h2>
                  <p className="text-lg text-gray-700 mb-6">{goal.description}</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {goal.details.map((detail, detailIndex) => (
                      <div key={detailIndex} className="flex items-start gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-700">{detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Implementation Section */}
        <div className="mt-16 bg-white rounded-lg p-8 shadow-md">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">Path Forward</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                1
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Community Engagement</h3>
              <p className="text-gray-600">
                Building awareness and support through education and peaceful advocacy.
              </p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                2
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Policy Advocacy</h3>
              <p className="text-gray-600">
                Working with local officials to implement transparent, rights-respecting policies.
              </p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                3
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Ongoing Oversight</h3>
              <p className="text-gray-600">
                Maintaining community vigilance to ensure policies are implemented and maintained.
              </p>
            </div>
          </div>
        </div>

        {/* Call to Action */}
        <div className="mt-16 text-center bg-blue-50 rounded-lg p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Support Our Mission</h2>
          <p className="text-gray-700 mb-6 max-w-2xl mx-auto">
            These changes require community support and sustained advocacy. Together, we can create 
            a system that respects constitutional rights while maintaining public safety.
          </p>
          <p className="text-sm text-gray-600">
            All advocacy efforts are conducted through peaceful, legal means in accordance with 
            constitutional principles and democratic processes.
          </p>
        </div>
      </div>
    </div>
  );
};

export default WhatWeWant;

