import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertCircle, ClipboardCheck, ArrowDownToLine, ArrowUpFromLine } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import _ from 'lodash';

const ClaudeDashboardHelper = () => {
  const [markdownInput, setMarkdownInput] = useState('');
  const [processedPrompt, setProcessedPrompt] = useState('');
  const [activeTab, setActiveTab] = useState('import');
  const [analysisType, setAnalysisType] = useState('health');
  const [requestType, setRequestType] = useState('analyze');

  const generateHealthPrompt = (data) => {
    const extractSection = (marker, endMarker) => {
      const start = data.indexOf(marker);
      const end = endMarker ? data.indexOf(endMarker, start) : data.length;
      return start >= 0 ? data.slice(start, end > start ? end : data.length) : '';
    };

    const healthMetrics = extractSection('| Wert | Aktuell |', 'Aktionspunkte:');
    const medications = extractSection('| Uhrzeit | Medikament |', 'Bei Bedarf:');
    const dailyTasks = extractSection('Tagesaufgaben:', 'Wissensbasis:');

    switch(requestType) {
      case 'analyze':
        return `Please analyze my current health dashboard data and provide insights:

${healthMetrics}

Current medications:
${medications}

Daily health tasks:
${dailyTasks}

Please provide:
1. Analysis of blood values and their implications
2. Recommendations for health optimization
3. Suggestions for daily routine improvements
4. Any concerning patterns or areas needing attention
5. Specific questions I should ask at my next appointment`;
      
      case 'optimize':
        return `Please help optimize my health tracking dashboard. Here's my current setup:

${data}

Please suggest:
1. Additional metrics I should track
2. Better organization of information
3. Important correlations to monitor
4. Automation opportunities
5. Ways to make the dashboard more actionable`;
      
      case 'summarize':
        return `Please provide a concise summary of my current health status based on this dashboard:

${data}

Focus on:
1. Key health indicators
2. Progress trends
3. Immediate action items
4. Upcoming important dates
5. Overall health trajectory`;
    }
  };

  const generateBusinessPrompt = (data) => {
    const businessSection = data.includes('Business |') ? 
      data.slice(data.indexOf('Business |'), data.indexOf('Beziehung |')) : '';
    
    switch(requestType) {
      case 'analyze':
        return `Please analyze my business dashboard and provide strategic insights:

${businessSection}

Please provide:
1. Analysis of current business status
2. Strategic recommendations
3. Priority action items
4. Resource optimization suggestions
5. Growth opportunities`;
      
      case 'optimize':
        return `Please help optimize my business tracking dashboard...`;
      
      case 'summarize':
        return `Please provide a concise summary of my business status...`;
    }
  };

  const handleGenerate = () => {
    try {
      let prompt;
      switch(analysisType) {
        case 'health':
          prompt = generateHealthPrompt(markdownInput);
          break;
        case 'business':
          prompt = generateBusinessPrompt(markdownInput);
          break;
        default:
          prompt = 'Please select an analysis type';
      }
      setProcessedPrompt(prompt);
      setActiveTab('export');
    } catch (error) {
      console.error('Processing error:', error);
      setProcessedPrompt('Error processing dashboard data. Please try again.');
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(processedPrompt);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <Card className="w-full max-w-4xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          Claude Dashboard Assistant
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="import">
              <ArrowDownToLine className="h-4 w-4 mr-2" />
              Import Dashboard
            </TabsTrigger>
            <TabsTrigger value="export">
              <ArrowUpFromLine className="h-4 w-4 mr-2" />
              Generated Prompt
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="import">
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <Select value={analysisType} onValueChange={setAnalysisType}>
                  <SelectTrigger className="w-[200px]">
                    <SelectValue placeholder="Select area" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="health">Health Dashboard</SelectItem>
                    <SelectItem value="business">Business Strategy</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={requestType} onValueChange={setRequestType}>
                  <SelectTrigger className="w-[200px]">
                    <SelectValue placeholder="Select request type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="analyze">Analyze Current State</SelectItem>
                    <SelectItem value="optimize">Optimize Dashboard</SelectItem>
                    <SelectItem value="summarize">Generate Summary</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Alert>
                <AlertDescription>
                  Paste your dashboard content to generate a Claude-optimized prompt
                </AlertDescription>
              </Alert>
              <Textarea 
                className="min-h-[400px] font-mono text-sm"
                placeholder="Paste dashboard markdown here..."
                value={markdownInput}
                onChange={(e) => setMarkdownInput(e.target.value)}
              />
              <Button onClick={handleGenerate} className="w-full">
                Generate Claude Prompt
              </Button>
            </div>
          </TabsContent>
          
          <TabsContent value="export">
            <div className="space-y-4">
              <Alert>
                <AlertDescription>
                  Copy this prompt and paste it into your Claude chat
                </AlertDescription>
              </Alert>
              <Textarea 
                className="min-h-[400px] font-mono text-sm"
                value={processedPrompt}
                readOnly
              />
              <Button 
                onClick={handleCopy}
                className="w-full"
              >
                <ClipboardCheck className="h-4 w-4 mr-2" />
                Copy to Clipboard
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};

export default ClaudeDashboardHelper;