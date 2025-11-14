const ProductAdvertisingAPIv1 = require('paapi5-nodejs-sdk');

const defaultClient = ProductAdvertisingAPIv1.ApiClient.instance;
defaultClient.accessKey = 'AKPAIHACU61762938637';
defaultClient.secretKey = 'VDxQfkqCpr6fQkOeHQZOtRI0u4yCELhrMZQ2oSCp';
defaultClient.host = 'webservices.amazon.ca';
defaultClient.region = 'us-east-1';

const api = new ProductAdvertisingAPIv1.DefaultApi();

const searchItemsRequest = new ProductAdvertisingAPIv1.SearchItemsRequest();
searchItemsRequest['PartnerTag'] = 'promopenguin-20';
searchItemsRequest['PartnerType'] = 'Associates';
searchItemsRequest['Keywords'] = 'laptop';
searchItemsRequest['SearchIndex'] = 'All';
searchItemsRequest['ItemCount'] = 2;
searchItemsRequest['Resources'] = ['ItemInfo.Title', 'Offers.Listings.Price'];

console.log('Making PAAPI request to amazon.ca...');
console.log('Host:', defaultClient.host);
console.log('Region:', defaultClient.region);

api.searchItems(searchItemsRequest, function(error, data, response) {
  if (error) {
    console.error('❌ Error:', error);
    console.log('Status Code:', error.status);
    console.log('Response:', error.response ? error.response.text : 'N/A');
  } else {
    console.log('✅ SUCCESS!');
    console.log('API called successfully');

    if (data.SearchResult && data.SearchResult.Items) {
      console.log(`Found ${data.SearchResult.Items.length} items`);
      data.SearchResult.Items.forEach((item, i) => {
        console.log(`\n[${i+1}] ${item.ASIN}`);
        if (item.ItemInfo && item.ItemInfo.Title) {
          console.log(`    Title: ${item.ItemInfo.Title.DisplayValue}`);
        }
      });
    }
  }
});
