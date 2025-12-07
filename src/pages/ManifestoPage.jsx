import { Eye, Shield, Lock, ChevronRight, Camera } from 'lucide-react';
import { Button } from '@/components/ui/button';

const ManifestoPage = () => {
    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-red-900 selection:text-white">
            {/* Hero Section */}
            <div className="relative overflow-hidden border-b border-red-900/30">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-red-900/10 via-slate-950 to-slate-950"></div>
                <div className="max-w-4xl mx-auto px-6 py-24 relative z-10 text-center">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-900/20 border border-red-900/50 text-red-500 text-xs font-mono mb-6 tracking-widest uppercase">
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                        </span>
                        System Status: Surveillance Active
                    </div>

                    <h1 className="text-5xl md:text-7xl font-bold mb-8 tracking-tight text-white">
                        WE ARE <span className="text-red-600">WATCHING</span><br />
                        THE WATCHERS
                    </h1>

                    <p className="text-xl md:text-2xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
                        Technology is a weapon. For too long, it has been pointed at us.
                        Now, we turn the lens around.
                    </p>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-3xl mx-auto px-6 py-20 space-y-24">

                {/* Section 1: The Blind Spot */}
                <section className="relative pl-8 border-l-2 border-red-900/50">
                    <Eye className="absolute -left-[25px] top-0 h-12 w-12 text-slate-950 fill-red-600 border-4 border-slate-950 rounded-full" />
                    <h2 className="text-3xl font-bold text-white mb-6 flex items-center gap-3">
                        The Blind Spot of 1984
                    </h2>
                    <div className="prose prose-invert prose-lg text-slate-400">
                        <p className="mb-4">
                            George Orwell's nightmare was a boot stamping on a human face, forever, seen through the unblinking eye of the Telescreen. The State saw everything; the citizen saw nothing.
                        </p>
                        <p>
                            But Orwell missed one thing. He didn't foresee that the Telescreen would fit in our pockets. He didn't predict that the surveillance machine would be dismantled and distributed to the very people it was meant to control.
                        </p>
                        <blockquote className="border-l-4 border-red-600 pl-4 italic text-slate-300 my-6">
                            "They have the satellites, the CCTV, and the drones. We have millions of eyes, millions of cameras, and we are everywhere."
                        </blockquote>
                    </div>
                </section>

                {/* Section 2: No More Excuses */}
                <section className="relative pl-8 border-l-2 border-slate-800">
                    <Shield className="absolute -left-[25px] top-0 h-12 w-12 text-slate-950 fill-slate-700 border-4 border-slate-950 rounded-full" />
                    <h2 className="text-3xl font-bold text-white mb-6">
                        The Death of "Just Following Orders"
                    </h2>
                    <div className="prose prose-invert prose-lg text-slate-400">
                        <p className="mb-4">
                            Anonymity is the shield of tyranny. When an officer hides their badge number, covers their face, or disappears into the ranks after brutalizing a protester, they rely on being nameless. They rely on the fog of war.
                        </p>
                        <p>
                            We are clearing the fog. We track badges. We map faces. We archive actions. When they say "I was just doing my job," we will pull up the record and show exactly what that job entailed.
                        </p>
                    </div>
                </section>

                {/* Section 3: The Tool */}
                <section className="bg-slate-900/50 p-8 rounded-2xl border border-slate-800">
                    <h2 className="text-3xl font-bold text-white mb-6 flex items-center gap-3">
                        <Camera className="text-red-500" />
                        The Weapon of Process
                    </h2>
                    <p className="text-slate-400 text-lg mb-8">
                        This platform is not just a gallery; it is a legal engine. Every upload is evidence. Every identification is a step toward accountability. We are building the dossier that history will read.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 bg-slate-950 rounded border border-slate-800 flex items-start gap-3">
                            <Lock className="h-5 w-5 text-green-500 mt-1" />
                            <div>
                                <h4 className="font-bold text-slate-200">Secure</h4>
                                <p className="text-sm text-slate-500">Evidence is decentralized and backed up.</p>
                            </div>
                        </div>
                        <div className="p-4 bg-slate-950 rounded border border-slate-800 flex items-start gap-3">
                            <Eye className="h-5 w-5 text-red-500 mt-1" />
                            <div>
                                <h4 className="font-bold text-slate-200">Public</h4>
                                <p className="text-sm text-slate-500">Transparency is our only protection.</p>
                            </div>
                        </div>
                    </div>
                </section>

                <div className="text-center pt-8">
                    <p className="text-slate-500 mb-6 italic">Big Brother is watching you. But who watches Big Brother?</p>
                    <Button size="lg" className="bg-red-600 hover:bg-red-700 text-white px-8 text-lg group">
                        Join the Watch
                        <ChevronRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                    </Button>
                </div>

            </div>
        </div>
    );
};

export default ManifestoPage;
