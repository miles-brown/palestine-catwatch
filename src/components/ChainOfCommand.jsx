import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Users, ChevronDown, ChevronUp, ChevronRight,
  Shield, Award, RefreshCw, Link2, Unlink, Search
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { API_BASE, getMediaUrl, fetchWithErrorHandling } from '../utils/api';
import { getRankColor } from '../utils/constants';

// Officer Card Component
const OfficerCard = ({ officer, isRoot = false, onSelectOfficer, selectedId }) => {
  const cropUrl = getMediaUrl(officer.crop_path);

  const isSelected = selectedId === officer.id;

  return (
    <div
      className={`
        relative p-4 rounded-lg border-2 cursor-pointer transition-all
        ${isSelected ? 'ring-2 ring-green-500 border-green-500' : 'border-gray-200 hover:border-green-300'}
        ${isRoot ? 'bg-gradient-to-br from-green-50 to-white' : 'bg-white'}
      `}
      onClick={() => onSelectOfficer(officer.id)}
    >
      <div className="flex items-center gap-3">
        {cropUrl ? (
          <img
            src={cropUrl}
            alt="Officer"
            className="w-14 h-14 rounded-full object-cover border-2 border-gray-200"
          />
        ) : (
          <div className="w-14 h-14 rounded-full bg-gray-200 flex items-center justify-center">
            <Users className="h-7 w-7 text-gray-400" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-gray-900 truncate">
            {officer.badge_number || `Officer #${officer.id}`}
          </div>
          {officer.rank && (
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getRankColor(officer.rank)}`}>
              <Award className="h-3 w-3 mr-1" />
              {officer.rank}
            </span>
          )}
          {officer.force && (
            <div className="text-xs text-gray-500 mt-1 truncate">
              {officer.force}
            </div>
          )}
        </div>
      </div>
      {officer.subordinate_count > 0 && (
        <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 bg-green-600 text-white text-xs px-2 py-0.5 rounded-full">
          {officer.subordinate_count} subordinate{officer.subordinate_count > 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
};

// Tree Node Component (recursive)
const TreeNode = ({ node, depth = 0, onSelectOfficer, selectedId, maxDepth = 5 }) => {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.subordinates && node.subordinates.length > 0;

  if (depth > maxDepth) return null;

  return (
    <div className="relative">
      {/* Vertical connector line from parent */}
      {depth > 0 && (
        <div className="absolute -top-6 left-1/2 w-0.5 h-6 bg-gray-300" />
      )}

      <div className="flex flex-col items-center">
        <OfficerCard
          officer={node}
          isRoot={depth === 0}
          onSelectOfficer={onSelectOfficer}
          selectedId={selectedId}
        />

        {hasChildren && (
          <button
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            className="mt-2 p-1 bg-gray-100 rounded-full hover:bg-gray-200 transition-colors"
          >
            {expanded ? (
              <ChevronUp className="h-4 w-4 text-gray-600" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-600" />
            )}
          </button>
        )}

        {hasChildren && expanded && (
          <div className="relative mt-6 pt-6">
            {/* Horizontal connector */}
            {node.subordinates.length > 1 && (
              <div className="absolute top-0 left-0 right-0 h-0.5 bg-gray-300" />
            )}
            {/* Vertical connectors to children */}
            <div className="absolute top-0 left-1/2 w-0.5 h-6 bg-gray-300" />

            <div className="flex gap-8 justify-center">
              {node.subordinates.map((sub) => (
                <TreeNode
                  key={sub.id}
                  node={sub}
                  depth={depth + 1}
                  onSelectOfficer={onSelectOfficer}
                  selectedId={selectedId}
                  maxDepth={maxDepth}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Chain Detail Panel
const ChainDetailPanel = ({ officerId, onClose, onLinkChanged }) => {
  const [chainData, setChainData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState(null);

  const fetchChain = useCallback(async () => {
    if (!officerId) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/officers/${officerId}/chain`);
      const data = await response.json();
      setChainData(data);
    } catch (error) {
      console.error("Failed to fetch chain:", error);
    } finally {
      setLoading(false);
    }
  }, [officerId]);

  useEffect(() => {
    fetchChain();
  }, [fetchChain]);

  const handleAutoLink = async () => {
    setLinking(true);
    setLinkError(null);
    try {
      const response = await fetch(`${API_BASE}/officers/${officerId}/auto-link-supervisor`, {
        method: 'POST'
      });
      const data = await response.json();

      if (data.status === 'error') {
        setLinkError(data.message);
      } else {
        // Refresh chain data
        fetchChain();
        if (onLinkChanged) onLinkChanged();
      }
    } catch (error) {
      setLinkError("Failed to auto-link supervisor");
    } finally {
      setLinking(false);
    }
  };

  const handleUnlink = async () => {
    try {
      await fetchWithErrorHandling(`${API_BASE}/officers/${officerId}/supervisor`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ supervisor_id: null })
      });
      fetchChain();
      if (onLinkChanged) onLinkChanged();
    } catch (error) {
      console.error("Failed to unlink:", error);
    }
  };

  if (!officerId) return null;

  const cropUrl = getMediaUrl(chainData?.officer?.crop_path);

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-6 h-full overflow-y-auto">
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : chainData ? (
        <div className="space-y-6">
          {/* Officer Info */}
          <div className="flex items-center gap-4 pb-4 border-b border-gray-200">
            {cropUrl ? (
              <img src={cropUrl} alt="Officer" className="w-20 h-20 rounded-full object-cover border-2 border-gray-200" />
            ) : (
              <div className="w-20 h-20 rounded-full bg-gray-200 flex items-center justify-center">
                <Users className="h-10 w-10 text-gray-400" />
              </div>
            )}
            <div>
              <h3 className="text-xl font-bold text-gray-900">
                {chainData.officer?.badge_number || `Officer #${officerId}`}
              </h3>
              {chainData.officer?.rank && (
                <span className={`inline-flex items-center px-2 py-1 rounded text-sm font-medium border ${getRankColor(chainData.officer.rank)}`}>
                  <Award className="h-4 w-4 mr-1" />
                  {chainData.officer.rank}
                </span>
              )}
              <p className="text-sm text-gray-500 mt-1">
                {chainData.officer?.force || 'Unknown Force'}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              onClick={handleAutoLink}
              disabled={linking}
              size="sm"
              className="flex-1"
            >
              {linking ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Link2 className="h-4 w-4 mr-2" />
              )}
              Auto-Link Supervisor
            </Button>
            {chainData.supervisors?.length > 0 && (
              <Button
                onClick={handleUnlink}
                variant="outline"
                size="sm"
              >
                <Unlink className="h-4 w-4" />
              </Button>
            )}
          </div>

          {linkError && (
            <p className="text-sm text-red-600 bg-red-50 p-2 rounded">{linkError}</p>
          )}

          {/* Supervisor Chain */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3">
              <ChevronUp className="h-4 w-4 inline mr-1" />
              Chain of Command (Upward)
            </h4>
            {chainData.supervisors?.length > 0 ? (
              <div className="space-y-2">
                {chainData.supervisors.map((sup, idx) => (
                  <div
                    key={sup.id}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border-l-4 border-green-500"
                    style={{ marginLeft: `${idx * 12}px` }}
                  >
                    <Shield className="h-5 w-5 text-green-600" />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">
                        {sup.badge_number || `Officer #${sup.id}`}
                      </div>
                      <div className="text-sm text-gray-500">
                        {sup.rank || 'Unknown Rank'} - {sup.force || 'Unknown Force'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 italic">No supervisor linked</p>
            )}
          </div>

          {/* Subordinates */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3">
              <ChevronDown className="h-4 w-4 inline mr-1" />
              Direct Reports
            </h4>
            {chainData.subordinates?.length > 0 ? (
              <div className="space-y-2">
                {chainData.subordinates.map((sub) => (
                  <div
                    key={sub.id}
                    className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border-l-4 border-blue-500"
                  >
                    <Users className="h-5 w-5 text-blue-600" />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">
                        {sub.badge_number || `Officer #${sub.id}`}
                      </div>
                      <div className="text-sm text-gray-500">
                        {sub.rank || 'Unknown Rank'} - {sub.force || 'Unknown Force'}
                      </div>
                    </div>
                    {sub.subordinate_count > 0 && (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                        +{sub.subordinate_count} subordinates
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 italic">No direct reports</p>
            )}
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500">
          Select an officer to view their chain of command
        </div>
      )}
    </div>
  );
};

// Main Chain of Command Component
const ChainOfCommand = () => {
  const [hierarchyTree, setHierarchyTree] = useState([]);
  const [selectedOfficerId, setSelectedOfficerId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredTree, setFilteredTree] = useState([]);

  const fetchHierarchy = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/officers/hierarchy?max_depth=5`);
      const data = await response.json();
      setHierarchyTree(data.hierarchy || []);
      setFilteredTree(data.hierarchy || []);
    } catch (error) {
      console.error("Failed to fetch hierarchy:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHierarchy();
  }, [fetchHierarchy]);

  // Filter tree based on search - memoized with cycle detection
  const filteredTreeMemo = useMemo(() => {
    if (!searchQuery.trim()) {
      return hierarchyTree;
    }

    const query = searchQuery.toLowerCase();

    // Filter with cycle detection to prevent infinite loops from circular references
    const filterNode = (node, visited = new Set()) => {
      // Cycle detection - if we've seen this node ID, skip it
      if (node.id && visited.has(node.id)) {
        console.warn('Circular reference detected in hierarchy:', node.id);
        return null;
      }

      // Add to visited set
      const newVisited = new Set(visited);
      if (node.id) newVisited.add(node.id);

      const matches =
        (node.badge_number && node.badge_number.toLowerCase().includes(query)) ||
        (node.force && node.force.toLowerCase().includes(query)) ||
        (node.rank && node.rank.toLowerCase().includes(query));

      const filteredSubs = node.subordinates
        ? node.subordinates.map(sub => filterNode(sub, newVisited)).filter(Boolean)
        : [];

      if (matches || filteredSubs.length > 0) {
        return { ...node, subordinates: filteredSubs };
      }
      return null;
    };

    return hierarchyTree.map(node => filterNode(node)).filter(Boolean);
  }, [searchQuery, hierarchyTree]);

  // Update filtered tree when memo changes
  useEffect(() => {
    setFilteredTree(filteredTreeMemo);
  }, [filteredTreeMemo]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b-2 border-green-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <Shield className="h-7 w-7 text-green-600" />
                Chain of Command
              </h1>
              <p className="text-gray-600 mt-1">
                Visualize officer hierarchy and supervisor relationships
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search officers..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
              </div>
              <Button onClick={fetchHierarchy} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Hierarchy Tree */}
          <div className="lg:col-span-2">
            <Card className="p-6 overflow-x-auto">
              <h2 className="text-lg font-semibold text-gray-900 mb-6">
                Organization Hierarchy
              </h2>

              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
                </div>
              ) : filteredTree.length > 0 ? (
                <div className="flex flex-wrap justify-center gap-12">
                  {filteredTree.map((rootOfficer) => (
                    <TreeNode
                      key={rootOfficer.id}
                      node={rootOfficer}
                      onSelectOfficer={setSelectedOfficerId}
                      selectedId={selectedOfficerId}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <Shield className="h-16 w-16 mx-auto mb-4 opacity-30" />
                  <p className="text-lg font-medium">No hierarchy data found</p>
                  <p className="text-sm mt-2">
                    {searchQuery
                      ? 'No officers match your search'
                      : 'Use auto-link or manually link supervisors to build the hierarchy'}
                  </p>
                </div>
              )}
            </Card>
          </div>

          {/* Detail Panel */}
          <div className="lg:col-span-1">
            <ChainDetailPanel
              officerId={selectedOfficerId}
              onClose={() => setSelectedOfficerId(null)}
              onLinkChanged={fetchHierarchy}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChainOfCommand;
