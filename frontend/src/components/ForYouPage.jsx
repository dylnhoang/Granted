import React, { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { supabase } from "../supabaseClient";
import WelcomeBanner from "./WelcomeBanner";

const categories = ["All", "STEM", "Arts", "first-gen", "BIPOC", "women", "low-income background", "LGBTQ+"];
const deadlines = ["All", "This Week", "This Month", "Flexible"];
const amounts = ["All", "<$500", "$500–$2,000", "$2,000+"];

function toTitleCase(str) {
  if (!str) return "";
  
  // Special cases that should remain unchanged
  const specialCases = {
    "all": "All",
    "stem": "STEM", 
    "bipoc": "BIPOC",
    "lgbtq+": "LGBTQ+"
  };
  
  // Check if the entire string is a special case
  if (specialCases[str.toLowerCase()]) {
    return specialCases[str.toLowerCase()];
  }
  
  return str
    .split(" ")
    .map(word => {
      const lowerWord = word.toLowerCase();
      // Check if this word is a special case
      if (specialCases[lowerWord]) {
        return specialCases[lowerWord];
      }
      // Handle acronyms (all caps words longer than 1 character)
      if (word === word.toUpperCase() && word.length > 1) {
        return word; // keep acronyms like STEM, USA, etc.
      }
      // Regular title case
      return word.charAt(0).toUpperCase() + word.substr(1).toLowerCase();
    })
    .join(" ");
}

function ForYouPage() {
  const { user } = useAuth();
  const [category, setCategory] = useState("All");
  const [deadline, setDeadline] = useState("All");
  const [amount, setAmount] = useState("All");
  const [grants, setGrants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedGrant, setSelectedGrant] = useState(null);

  useEffect(() => {
    async function fetchGrants() {
      setLoading(true);
      try {
        // Fetch grants from your existing Supabase table
        const { data, error } = await supabase
          .from('grants')
          .select('*')
          .order('created_at', { ascending: false });

        if (error) {
          console.error('Error fetching grants:', error);
          setGrants([]);
        } else {
          console.log('Fetched grants:', data);
          setGrants(data || []);
          if (data && data.length > 0) {
            setSelectedGrant(data[0]);
          }
        }
      } catch (error) {
        console.error('Error fetching grants:', error);
        setGrants([]);
      } finally {
        setLoading(false);
      }
    }
    fetchGrants();
  }, []);

  // Defensive filter logic
  const filteredGrants = (grants || []).filter((grant) => {
    // Check both sectors and eligibility_criteria for category matching
    const categoryMatch = category === "All" || 
      (grant.sectors || []).includes(category) || 
      (grant.eligibility_criteria || []).includes(category);
    
    console.log(`Grant: ${grant.title}, Category: ${category}, Sectors: ${grant.sectors}, Eligibility: ${grant.eligibility_criteria}, Match: ${categoryMatch}`);
    
    const deadlineMatch =
      deadline === "All" || grant.deadline === deadline;
    let amountMatch = true;
    if (amount === "<$500") amountMatch = parseInt((grant.amount || "0").replace(/[^0-9]/g, "")) < 500;
    else if (amount === "$500–$2,000") {
      const val = parseInt((grant.amount || "0").replace(/[^0-9]/g, ""));
      amountMatch = val >= 500 && val <= 2000;
    } else if (amount === "$2,000+") amountMatch = parseInt((grant.amount || "0").replace(/[^0-9]/g, "")) > 2000;
    return categoryMatch && deadlineMatch && amountMatch;
  });

  if (loading) {
    return <div className="text-center py-8">Loading grants...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-12">
      {/* Welcome Banner */}
      <WelcomeBanner />
      
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 py-8 px-4 sm:px-8 mb-4">
        <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-2">
          GrantFinder
        </h1>
        <p className="text-gray-100 text-lg">Discover scholarships and grants tailored to your journey.</p>
      </div>

      {/* Filter Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-8 mb-4">
        <div className="flex flex-col md:flex-row gap-4 md:gap-6 bg-white rounded-xl shadow p-4 md:p-6">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {(categories || []).map((cat) => (
                <option key={cat} value={cat}>{toTitleCase(cat)}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Deadline</label>
            <select
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
            >
              {(deadlines || []).map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Award Amount</label>
            <select
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            >
              {(amounts || []).map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Main Content: Two Column Layout */}
      <div className="max-w-7xl mx-auto px-4 sm:px-8 flex flex-col lg:flex-row gap-6 min-h-[60vh]">
        {/* Sidebar: Grant List */}
        <div className="lg:w-1/3 w-full bg-white rounded-xl shadow p-4 overflow-y-auto max-h-[70vh]">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Grant Matches</h2>
          <div className="flex flex-col gap-3">
            {(filteredGrants || []).length === 0 ? (
              <div className="text-center text-gray-500 py-12">No grants found for your filters.</div>
            ) : (
              (filteredGrants || []).map((grant) => (
                <button
                  key={grant.id}
                  onClick={() => setSelectedGrant(grant)}
                  className={`text-left rounded-lg border transition p-4 shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary ${
                    selectedGrant && selectedGrant.id === grant.id
                      ? "border-primary bg-primary/10"
                      : "border-gray-200 bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-gray-900">{(grant.title)}</span>
                    <span className="bg-primary/20 text-primary text-xs font-semibold px-2 py-1 rounded-full">
                      {/* You can calculate match % or show a static badge if needed */}
                      Match
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 mb-1">
                    {(grant.target_group || []).map((group) => toTitleCase(group)).join(", ")}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(grant.sectors || []).map((tag) => (
                      <span
                        key={tag}
                        className="bg-gray-100 text-gray-700 text-xs px-2 py-0.5 rounded-full"
                      >
                        {toTitleCase(tag)}
                      </span>
                    ))}
                  </div>
                  <div className="text-xs text-gray-500 mt-2">Due {grant.deadline}</div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Main Panel: Grant Details */}
        <div className="flex-1 bg-white rounded-xl shadow p-6 flex flex-col">
          {selectedGrant ? (
            <>
              <div className="flex items-center justify-between mb-2">
                <h2 className="font-bold text-2xl text-gray-900">{(selectedGrant.title)}</h2>
                <span className="bg-primary/20 text-primary text-sm font-semibold px-3 py-1 rounded-full">
                  {/* You can calculate match % or show a static badge if needed */}
                  Match
                </span>
              </div>
              <div className="text-md text-gray-700 mb-1">{(selectedGrant.organization)}</div>
              <div className="flex flex-wrap gap-2 mb-3">
                {(selectedGrant?.sectors || []).map((tag) => (
                  <span key={tag} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full">
                    {toTitleCase(tag)}
                  </span>
                ))}
                {(selectedGrant?.eligibility_criteria || []).map((tag) => (
                  <span key={tag} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full">
                    {toTitleCase(tag)}
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-4 mb-4">
                <div className="text-sm text-gray-500">Due <span className="font-semibold">{selectedGrant.deadline}</span></div>
                <div className="text-sm text-gray-500">Award: <span className="font-semibold">{selectedGrant.amount}</span></div>
              </div>
              <div className="text-gray-800 mb-6 grant-description">
                <div 
                  className="whitespace-pre-line"
                  dangerouslySetInnerHTML={{ 
                    __html: (selectedGrant.description || "")
                      .split(/\r?\n/)
                      .map(para => para.trim() ? `<p class="mb-3">${para}</p>` : '')
                      .join('')
                  }}
                />
              </div>
              <div className="mt-auto">
                <a
                  href={selectedGrant.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-primary hover:bg-primary/80 text-white text-base font-semibold px-6 py-3 rounded-md shadow focus:outline-none focus:ring-primary inline-block mt-4"
                >
                  Apply
                </a>
              </div>
            </>
          ) : (
            <div className="text-gray-500 text-center my-auto">Select a grant to see details.</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ForYouPage; 