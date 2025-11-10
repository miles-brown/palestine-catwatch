import { Users, Megaphone, Eye } from 'lucide-react';
import { Card } from '@/components/ui/card';

const OurStory = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              Our Story
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Born from a commitment to transparency and the fundamental right to peaceful protest.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Introduction */}
        <div className="prose prose-lg max-w-none mb-12">
          <p className="text-lg text-gray-700 leading-relaxed mb-6">
            The Accountability Campaign emerged from the recognition that transparency and documentation 
            are essential pillars of a democratic society. During peaceful demonstrations advocating for 
            justice and human rights, we witnessed the critical importance of maintaining accurate records 
            of police interactions with protesters.
          </p>
          
          <p className="text-lg text-gray-700 leading-relaxed mb-6">
            Our mission began during the Palestine solidarity protests, where we observed the need for 
            systematic documentation of law enforcement activities. We believe that both protesters and 
            police officers benefit from transparent, factual record-keeping that promotes accountability 
            and protects everyone's rights.
          </p>
        </div>

        {/* Values Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          <Card className="p-6 text-center">
            <Eye className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Transparency</h3>
            <p className="text-gray-600">
              We believe in open, factual documentation that serves the public interest and promotes understanding.
            </p>
          </Card>
          
          <Card className="p-6 text-center">
            <Users className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Accountability</h3>
            <p className="text-gray-600">
              Every public servant should be accountable to the communities they serve, with clear documentation of their actions.
            </p>
          </Card>
          
          <Card className="p-6 text-center">
            <Megaphone className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Rights Protection</h3>
            <p className="text-gray-600">
              We defend the fundamental rights to freedom of speech, assembly, and peaceful protest for all citizens.
            </p>
          </Card>
        </div>

        {/* Our Approach */}
        <div className="bg-white rounded-lg p-8 shadow-md mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Our Approach</h2>
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-700">
                <strong>Evidence-Based Documentation:</strong> We rely exclusively on publicly available 
                materials including videos, photographs, social media posts, and news reports.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-700">
                <strong>Factual Reporting:</strong> Our documentation focuses on observable actions and 
                verifiable information, avoiding speculation or inflammatory language.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-700">
                <strong>Source Transparency:</strong> Every piece of information is linked to its original 
                source, allowing visitors to verify and examine the evidence themselves.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"></div>
              <p className="text-gray-700">
                <strong>Respectful Presentation:</strong> We maintain a professional, respectful tone while 
                advocating for transparency and accountability in law enforcement.
              </p>
            </div>
          </div>
        </div>

        {/* Call to Action */}
        <div className="text-center bg-blue-50 rounded-lg p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Join Our Mission</h2>
          <p className="text-gray-700 mb-6">
            Transparency and accountability require community engagement. Together, we can build a more 
            just and transparent society where everyone's rights are protected and respected.
          </p>
          <p className="text-sm text-gray-600">
            This campaign is committed to peaceful advocacy and the protection of constitutional rights 
            for all members of our community.
          </p>
        </div>
      </div>
    </div>
  );
};

export default OurStory;

