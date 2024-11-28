import unittest
from pathlib import Path
from ai_sync import AITemplateSync
import os
import shutil
import re

class TestAISync(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path('test_templates')
        self.test_dir.mkdir(exist_ok=True)
        
        # Create a test template with sample data
        self.test_template = self.test_dir / 'test_business_center.md'
        test_content = """# Business Center

## Tasks & Activities
- Complete market research report
- Update financial projections
- Schedule team meeting
- Review competitor analysis

## Business Metrics
- Revenue: 150000
- Growth Rate: 15%
- Customer Satisfaction: 4.8
- Churn Rate: 2.5%

## Goals
- Increase market share by 10%
- Launch new product line
- Expand to international markets
- Improve customer retention

## Challenges
- Limited resources
- Strong competition
- Market uncertainty
- Technical debt

## Opportunities
- Emerging markets
- New technologies
- Strategic partnerships
- Customer feedback

## Skills Development
### Technical Skills
- Python programming
- Data analysis
- Cloud infrastructure
- AI/ML implementation

### Business Skills
- Project management
- Strategic planning
- Financial analysis
- Market research

### Soft Skills
- Leadership
- Communication
- Problem-solving
- Team collaboration

## AI Integration
[[AI_Content_Suggestions]]
[[Health_Metrics]]
[[Financial_Forecast]]
[[Market_Analysis]]
[[AI_Wellness_Score]]
[[AI_Generated_Goal]]
[[Weekly_AI_Report]]
[[AI_Skills_Development]]

Last Updated: [[Timestamp]]
"""
        with open(self.test_template, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        self.ai_sync = AITemplateSync()
        
    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        
    def test_extract_activities(self):
        """Test activity extraction."""
        with open(self.test_template, 'r', encoding='utf-8') as f:
            content = f.read()
            
        activities = self.ai_sync.extract_activities(content)
        
        # Verify extracted activities
        self.assertEqual(len(activities), 4)
        self.assertIn('Complete market research report', activities)
        self.assertIn('Update financial projections', activities)
        self.assertIn('Schedule team meeting', activities)
        self.assertIn('Review competitor analysis', activities)
        
    def test_extract_business_data(self):
        """Test business data extraction."""
        with open(self.test_template, 'r', encoding='utf-8') as f:
            content = f.read()
            
        business_data = self.ai_sync.extract_business_data(content)
        
        # Verify metrics
        self.assertEqual(business_data['metrics']['Revenue'], 150000)
        self.assertEqual(business_data['metrics']['Growth Rate'], 15)
        self.assertEqual(business_data['metrics']['Customer Satisfaction'], 4.8)
        self.assertEqual(business_data['metrics']['Churn Rate'], 2.5)
        
        # Verify goals
        self.assertEqual(len(business_data['goals']), 4)
        self.assertIn('Increase market share by 10%', business_data['goals'])
        
        # Verify challenges
        self.assertEqual(len(business_data['challenges']), 4)
        self.assertIn('Limited resources', business_data['challenges'])
        
        # Verify opportunities
        self.assertEqual(len(business_data['opportunities']), 4)
        self.assertIn('Emerging markets', business_data['opportunities'])
        
    def test_extract_skills_needed(self):
        """Test skills extraction."""
        with open(self.test_template, 'r', encoding='utf-8') as f:
            content = f.read()
            
        skills = self.ai_sync.extract_skills_needed(content)
        
        # Verify technical skills
        self.assertEqual(len(skills['technical']), 4)
        self.assertIn('Python programming', skills['technical'])
        self.assertIn('Data analysis', skills['technical'])
        
        # Verify business skills
        self.assertEqual(len(skills['business']), 4)
        self.assertIn('Project management', skills['business'])
        self.assertIn('Strategic planning', skills['business'])
        
        # Verify soft skills
        self.assertEqual(len(skills['soft']), 4)
        self.assertIn('Leadership', skills['soft'])
        self.assertIn('Communication', skills['soft'])
        
    def test_ai_content_generation(self):
        """Test AI content generation."""
        with open(self.test_template, 'r', encoding='utf-8') as f:
            content = f.read()
            
        ai_content = self.ai_sync.generate_ai_content(content)
        
        # Verify AI content structure
        self.assertIsInstance(ai_content, dict)
        self.assertIn('content_suggestions', ai_content)
        self.assertIn('health_metrics', ai_content)
        self.assertIn('financial_forecast', ai_content)
        self.assertIn('market_analysis', ai_content)
        self.assertIn('wellness_score', ai_content)
        
    def test_template_update(self):
        """Test template updating with AI content."""
        test_ai_content = {
            'content_suggestions': ['Test Suggestion 1', 'Test Suggestion 2'],
            'health_metrics': {'energy': 8, 'stress': 4},
            'financial_forecast': {'revenue': 1000, 'growth': 0.1},
            'market_analysis': {'trend': 'positive'},
            'wellness_score': 7.5,
            'ai_goals': {'short_term': ['Goal 1'], 'long_term': ['Goal 2']},
            'weekly_report': {'achievements': ['Achievement 1']},
            'learning_path': {'courses': ['Course 1']}
        }
        
        with open(self.test_template, 'r', encoding='utf-8') as f:
            content = f.read()
            
        updated_content = self.ai_sync.update_template_with_ai(content, test_ai_content)
        
        # Verify placeholders are replaced
        self.assertNotIn("[[AI_Content_Suggestions]]", updated_content)
        self.assertNotIn("[[Health_Metrics]]", updated_content)
        self.assertIn("Test Suggestion 1", updated_content)
        self.assertIn("energy: 8", updated_content)
        
    def test_content_chunking(self):
        """Test content chunking functionality."""
        long_content = "\n".join([f"## Section {i}\nContent {i}" for i in range(100)])
        chunks = self.ai_sync.split_content_into_chunks(long_content, max_blocks=10)
        
        # Verify chunks are created correctly
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.split('\n')), 10)

    def test_extract_business_metrics(self):
        """Test extraction of business metrics."""
        test_content = """
## Business Metrics
### Financial Metrics
- Revenue: €10,000
- Growth Rate: 10%
- Profit Margin: 20%
- Burn Rate: €5,000
- CAC: €100
- LTV: €1,000

### Customer Metrics
- Active Users: 1000
- Churn Rate: 5%
- NPS Score: 40
- Customer Satisfaction: 80%
- Response Time: 2 hours

### Team Metrics
- Team Size: 5
- Productivity Score: 80%
- Engagement Level: 90%
- Retention Rate: 95%
"""
        sync = AITemplateSync()
        metrics = sync.extract_business_metrics(test_content)
        
        # Test financial metrics
        self.assertEqual(metrics['financial']['revenue'], '€10,000')
        self.assertEqual(metrics['financial']['growth_rate'], '10')
        self.assertEqual(metrics['financial']['profit_margin'], '20')
        self.assertEqual(metrics['financial']['burn_rate'], '€5,000')
        self.assertEqual(metrics['financial']['cac'], '€100')
        self.assertEqual(metrics['financial']['ltv'], '€1,000')
        
        # Test customer metrics
        self.assertEqual(metrics['customer']['active_users'], '1000')
        self.assertEqual(metrics['customer']['churn_rate'], '5')
        self.assertEqual(metrics['customer']['nps_score'], '40')
        self.assertEqual(metrics['customer']['csat'], '80')
        self.assertEqual(metrics['customer']['response_time'], '2 hours')
        
        # Test team metrics
        self.assertEqual(metrics['team']['size'], '5')
        self.assertEqual(metrics['team']['productivity'], '80')
        self.assertEqual(metrics['team']['engagement'], '90')
        self.assertEqual(metrics['team']['retention'], '95')

    def test_extract_health_metrics(self):
        """Test extraction of health metrics."""
        test_content = """
## Health Impact
### Energy Levels
- 8/10

### Stress Indicators
- 6/10

### Work-Life Balance
- 7/10
"""
        sync = AITemplateSync()
        health = sync.extract_health_metrics(test_content)
        
        self.assertEqual(health['energy'], '8')
        self.assertEqual(health['stress'], '6')
        self.assertEqual(health['work_life_balance'], '7')

    def test_extract_resource_allocation(self):
        """Test extraction of resource allocation."""
        test_content = """
## Resource Allocation
### Time Distribution
- 50% of time allocated to YouTube
- 30% of time allocated to taxi
- 20% of time allocated to restaurant

### Budget Distribution
- 50% of budget allocated to marketing
- 30% of budget allocated to employee salaries
- 20% of budget allocated to equipment

### Team Distribution
- 2 team members allocated to YouTube
- 2 team members allocated to taxi
- 1 team member allocated to restaurant
"""
        sync = AITemplateSync()
        allocation = sync.extract_resource_allocation(test_content)
        
        # Test time distribution
        self.assertEqual(allocation['time']['youtube'], '50')
        self.assertEqual(allocation['time']['taxi'], '30')
        self.assertEqual(allocation['time']['restaurant'], '20')
        
        # Test budget distribution
        self.assertEqual(allocation['budget']['marketing'], '50')
        self.assertEqual(allocation['budget']['salaries'], '30')
        self.assertEqual(allocation['budget']['equipment'], '20')
        
        # Test team distribution
        self.assertEqual(allocation['team']['youtube'], '2')
        self.assertEqual(allocation['team']['taxi'], '2')
        self.assertEqual(allocation['team']['restaurant'], '1')

    def test_generate_business_insights(self):
        """Test generation of business insights."""
        sync = AITemplateSync()
        
        # Test data
        metrics = {
            'financial': {
                'revenue': '€10,000',
                'profit_margin': '15',
                'burn_rate': '€6,000'
            },
            'customer': {
                'churn_rate': '7',
                'nps_score': '35'
            },
            'team': {
                'engagement': '75',
                'productivity': '70',
                'retention': '85'
            }
        }
        
        health = {
            'energy': '6',
            'stress': '7',
            'work_life_balance': '6'
        }
        
        allocation = {
            'time': {
                'youtube': '60',
                'taxi': '50',
                'restaurant': '20'
            },
            'budget': {
                'marketing': '70',
                'equipment': '5'
            },
            'team': {
                'youtube': '1',
                'taxi': '2',
                'restaurant': '1'
            }
        }
        
        insights = sync.generate_business_insights(metrics, health, allocation)
        
        # Test performance analysis
        self.assertIn('Consider strategies to improve profit margins', insights['performance_analysis'])
        self.assertIn('High churn rate - investigate customer satisfaction', insights['performance_analysis'])
        self.assertIn('Team engagement could be improved', insights['performance_analysis'])
        
        # Test health recommendations
        self.assertIn('Consider adjusting work schedule for better energy management', insights['health_recommendations'])
        self.assertIn('Implement stress management techniques', insights['health_recommendations'])
        self.assertIn('Review and adjust work-life boundaries', insights['health_recommendations'])
        
        # Test resource optimization
        self.assertIn('Time allocation exceeds 100% - review commitments', insights['resource_optimization'])
        self.assertIn('High marketing spend - evaluate ROI', insights['resource_optimization'])
        self.assertIn('Consider increasing equipment investment', insights['resource_optimization'])
        
        # Test risk assessment
        self.assertIn('High burn rate relative to revenue', insights['risk_assessment'])
        self.assertIn('Team retention risk - review HR policies', insights['risk_assessment'])

    def test_update_template_with_ai(self):
        """Test template update with AI insights."""
        sync = AITemplateSync()
        
        test_template = """# Business Dashboard
[[Timestamp]]

## Performance
[[AI_Performance_Analysis]]

## Health
[[Health_Metrics]]

## Resources
[[Resource_Optimization]]

## Risks
[[Business_Risks]]
"""
        
        # Update template
        updated_content = sync.update_template_with_ai(test_template)
        
        # Verify timestamp was updated
        self.assertNotIn("[[Timestamp]]", updated_content)
        self.assertRegex(updated_content, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
        
        # Verify sections were updated
        self.assertNotIn("[[AI_Performance_Analysis]]", updated_content)
        self.assertNotIn("[[Health_Metrics]]", updated_content)
        self.assertNotIn("[[Resource_Optimization]]", updated_content)
        self.assertNotIn("[[Business_Risks]]", updated_content)
        
        # Verify insights were added
        self.assertIn("### Performance Analysis", updated_content)
        self.assertIn("### Health Recommendations", updated_content)
        self.assertIn("### Resource Optimization", updated_content)
        self.assertIn("### Risk Assessment", updated_content)

    def test_update_section(self):
        """Test section update helper method."""
        sync = AITemplateSync()
        
        content = "Hello [[TEST]] World"
        updated = sync._update_section(content, "[[TEST]]", "Python")
        self.assertEqual(updated, "Hello Python World")
        
        # Test with missing placeholder
        content = "Hello World"
        updated = sync._update_section(content, "[[TEST]]", "Python")
        self.assertEqual(updated, "Hello World")

    def test_generate_weekly_summary(self):
        """Test weekly summary generation."""
        sync = AITemplateSync()
        
        # Test data
        metrics = {
            'financial': {
                'revenue': '€20,000',
                'profit_margin': '25',
                'burn_rate': '€5,000'
            },
            'customer': {
                'nps_score': '45',
                'csat': '85'
            },
            'team': {
                'productivity': '85',
                'retention': '95'
            }
        }
        
        health = {
            'energy': '8',
            'stress': '4',
            'work_life_balance': '7'
        }
        
        allocation = {
            'time': {
                'youtube': '40',
                'taxi': '30',
                'restaurant': '20'
            },
            'budget': {
                'marketing': '50',
                'salaries': '30',
                'equipment': '20'
            },
            'team': {
                'youtube': '2',
                'taxi': '2',
                'restaurant': '1'
            }
        }
        
        insights = {
            'performance_analysis': [
                'Strong revenue growth',
                'Consider expanding team'
            ],
            'health_recommendations': [
                'Maintain current exercise routine',
                'Consider more breaks'
            ],
            'resource_optimization': [
                'Optimize time allocation',
                'Review marketing spend'
            ],
            'risk_assessment': [
                'Monitor market competition'
            ]
        }
        
        summary = sync.generate_weekly_summary(metrics, health, allocation, insights)
        
        # Test achievements
        self.assertIn('Strong profit margins maintained', summary['achievements'])
        self.assertIn('Healthy NPS score achieved', summary['achievements'])
        self.assertIn('Strong team productivity', summary['achievements'])
        
        # Test challenges
        self.assertIn('Consider expanding team', summary['challenges'])
        self.assertIn('Monitor market competition', summary['challenges'])
        
        # Test focus areas
        self.assertIn('Optimize time allocation', summary['focus_areas'])
        self.assertIn('Consider more breaks', summary['focus_areas'])
        
        # Test health status
        self.assertIn('Health Status: Good', summary['health_status'])
        
        # Test resource status
        self.assertIn('Time Allocation: 90% utilized', summary['resource_status'])
        self.assertIn('Team Size: 5 members', summary['resource_status'])

if __name__ == '__main__':
    unittest.main()
