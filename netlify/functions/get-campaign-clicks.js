const { createClient } = require('@supabase/supabase-js');

exports.handler = async (event) => {
  const campaignId = event.queryStringParameters.campaign_id;
  const authHeader = event.headers.authorization;

  if (!campaignId) {
    return {
      statusCode: 400,
      body: JSON.stringify({ success: false, message: 'campaign_id parameter is missing.' }),
    };
  }

  if (!authHeader || authHeader !== `Bearer ${process.env.YOUR_SECRET_API_KEY}`) {
    return {
      statusCode: 401,
      body: JSON.stringify({ success: false, message: 'Unauthorized.' }),
    };
  }

  const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

  try {
    const { data, error } = await supabase
      .from('report_clicks')
      .select('*')
      .eq('utm_campaign', `campaign_${campaignId}`);

    if (error) {
      throw error;
    }

    if (!data || data.length === 0) {
      return {
        statusCode: 404,
        body: JSON.stringify({
          success: false,
          campaign_id: campaignId,
          message: 'No clicks found for this campaign_id.',
        }),
      };
    }

    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        campaign_id: campaignId,
        clicks: data,
      }),
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ success: false, message: 'Internal Server Error', error: error.message }),
    };
  }
};
